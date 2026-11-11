from collections import defaultdict
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Avg, Count, F, FloatField, Func, QuerySet, Sum
from django.db.models.functions import Exp, Greatest
from django.utils import timezone

from apps.accounts.models import User
from apps.core import kinds
from apps.core.exceptions import DomainError
from apps.library.models import Collection, CollectionItem, Download, Favorite
from apps.moderation import services as moderation
from apps.moderation import words
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import Review, ReviewVote

BAYES_WEIGHT = 10  # C in score = (C·m + Σstars) / (C + n)
#: Who hears about a new review: authors of packs, owners of servers (mods have neither)
REVIEW_NOTICES = {
    "pack": Notification.Type.REVIEW_ON_YOUR_PACK,
    "server": Notification.Type.REVIEW_ON_YOUR_SERVER,
}


# Reviews


def recompute_rating(*, content_type: ContentType, object_id: int) -> None:
    """Exact average and count of published reviews on the target."""
    stats = Review.objects.filter(
        content_type=content_type, object_id=object_id, status=Review.Status.PUBLISHED
    ).aggregate(avg=Avg("stars"), count=Count("pk"))
    content_type.model_class()._base_manager.filter(pk=object_id).update(
        rating_avg=round(stats["avg"] or 0, 2), rating_count=stats["count"]
    )


@transaction.atomic
def upsert_review(
    *, user: User, kind: str, identifier: str, stars: int, text: str = ""
) -> tuple[Review, bool]:
    """One review per player and object: a second one updates the first."""
    kind_obj, target = kinds.resolve(kind, identifier, viewer=user, action="review")
    owner = kind_obj.owner_of(target)
    if owner is not None and owner.pk == user.pk:
        raise DomainError(code="own_object", message="Власний проєкт оцінити не можна.")
    moderation.ensure_can_publish(user)
    words.check(text=text)
    review, created = Review.objects.update_or_create(
        user=user,
        content_type=kind_obj.content_type,
        object_id=target.pk,
        defaults={"stars": stars, "text": text.strip()},
    )
    recompute_rating(content_type=kind_obj.content_type, object_id=target.pk)
    notice = REVIEW_NOTICES.get(kind_obj.name)
    if created and notice and _answerer(kind_obj, target) is not None:
        notify(user=owner, type=notice, target=target, actor=user.nickname, excerpt=review.text)
    return review, created


def can_reply(*, kind: kinds.Kind, target, user) -> bool:
    owner = _answerer(kind, target)
    return bool(owner is not None and user.is_authenticated and owner.pk == user.pk)


def _answerer(kind: kinds.Kind, target) -> User | None:
    """Who may answer reviews: the author of a community pack, the proven owner of a server."""
    if kind.name == "pack" and target.origin != "community":
        return None  # a Modrinth modpack has no author here
    if kind.name == "server" and not target.is_verified:
        return None
    return kind.owner_of(target) if kind.name in REVIEW_NOTICES else None


@transaction.atomic
def reply_to_review(*, review: Review, user: User, text: str) -> Review:
    """The author of a community pack or the proven owner of a server answers a review
    of their work (one answer, editable; empty removes it). The reviewer is told once."""
    kind = kinds.kind_for_model(review.content_type.model_class())
    owner = _answerer(kind, review.target) if review.target is not None else None
    if owner is None or owner.pk != user.pk:
        raise DomainError(
            code="forbidden", message="Відповідати може лише автор чи власник.", status=403
        )
    moderation.ensure_can_publish(user)
    text = text.strip()
    words.check(text=text)
    first = not review.reply_text and bool(text)
    review.reply_text = text
    review.reply_by = user if text else None
    review.replied_at = timezone.now() if text else None
    review.save(update_fields=["reply_text", "reply_by", "replied_at", "updated_at"])
    if first:
        notify(
            user=review.user,
            type=Notification.Type.REVIEW_REPLY,
            target=review.target,
            actor=user.nickname,
            excerpt=text,
        )
    return review


@transaction.atomic
def delete_review(*, review: Review, user: User) -> None:
    if review.user_id != user.pk and not user.is_moderator:
        raise DomainError(code="forbidden", message="Це не твій відгук.", status=403)
    content_type, object_id = review.content_type, review.object_id
    review.delete()
    recompute_rating(content_type=content_type, object_id=object_id)


@transaction.atomic
def vote_review(*, review: Review, user: User, is_helpful: bool) -> Review:
    if review.user_id == user.pk:
        raise DomainError(code="own_review", message="Свій відгук оцінити не можна.")
    ReviewVote.objects.update_or_create(
        user=user, review=review, defaults={"is_helpful": is_helpful}
    )
    review.helpful_count = review.votes.filter(is_helpful=True).count()
    review.save(update_fields=["helpful_count"])
    return review


def recalc_scores() -> dict[str, int]:
    """Bayesian average for review kinds, saves for the rest; stored in `score`."""
    updated: dict[str, int] = {}
    for kind in kinds.all_kinds():
        model = kind.model
        if kind.rating == "favorites":
            updated[kind.name] = model._base_manager.update(score=F("favorites_count"))
            continue
        stats = list(
            Review.objects.filter(content_type=kind.content_type, status=Review.Status.PUBLISHED)
            .values("object_id")
            .annotate(n=Count("pk"), total=Sum("stars"))
        )
        reviews = sum(row["n"] for row in stats)
        mean = sum(row["total"] for row in stats) / reviews if reviews else 0.0
        model._base_manager.update(score=mean)
        objects = model._base_manager.in_bulk([row["object_id"] for row in stats])
        for row in stats:
            obj = objects.get(row["object_id"])
            if obj is not None:
                obj.score = (BAYES_WEIGHT * mean + row["total"]) / (BAYES_WEIGHT + row["n"])
        model._base_manager.bulk_update(objects.values(), ["score"], batch_size=500)
        updated[kind.name] = len(objects)
    return updated


# Trends: trend = Σ w · e^(−age_hours / 48) over the last 14 days (docs/tech.md, 9)

TREND_WINDOW = timedelta(days=14)
TREND_DECAY_HOURS = 48
TREND_WEIGHTS = {"favorite": 2.0, "download": 0.5, "review": 3.0}


def _decayed_sum(queryset: QuerySet, *, group_by: str, weight: float, now) -> dict[int, float]:
    epoch = Func(
        F("created_at"),
        function="EXTRACT",
        template="EXTRACT(EPOCH FROM %(expressions)s)",
        output_field=FloatField(),
    )
    decay = Exp((epoch - now.timestamp()) / (TREND_DECAY_HOURS * 3600.0))
    rows = (
        queryset.filter(created_at__gte=now - TREND_WINDOW)
        .values(group_by)
        .annotate(trend=Sum(decay, output_field=FloatField()))
        .order_by()
    )
    return {row[group_by]: weight * row["trend"] for row in rows}


def recalc_trends(*, now=None) -> dict[str, int]:
    """Recent saves, downloads and reviews; older events fade out."""
    now = now or timezone.now()
    updated: dict[str, int] = {}
    for kind in kinds.all_kinds():
        target = {"content_type": kind.content_type}
        trends: dict[int, float] = defaultdict(float)
        sources = [
            (Favorite.objects.filter(**target), "object_id", TREND_WEIGHTS["favorite"]),
            (
                Review.objects.filter(**target, status=Review.Status.PUBLISHED),
                "object_id",
                TREND_WEIGHTS["review"],
            ),
        ]
        if kind.name == "mod":
            sources.append((Download.objects.all(), "project_id", TREND_WEIGHTS["download"]))
        for queryset, group_by, weight in sources:
            for pk, value in _decayed_sum(
                queryset, group_by=group_by, weight=weight, now=now
            ).items():
                trends[pk] += value
        model = kind.model
        model._base_manager.exclude(pk__in=trends).exclude(trend_score=0).update(trend_score=0)
        objects = model._base_manager.in_bulk(list(trends))
        for pk, obj in objects.items():
            obj.trend_score = round(trends[pk], 4)
        model._base_manager.bulk_update(objects.values(), ["trend_score"], batch_size=500)
        updated[kind.name] = len(objects)
    return updated


# Cleanup


@transaction.atomic
def forget_target(*, kind: kinds.Kind, object_id: int) -> None:
    """Removes everything that points at a deleted object and fixes collection counters."""
    target = {"content_type": kind.content_type, "object_id": object_id}
    items = CollectionItem.objects.filter(**target)
    for row in items.values("collection_id").annotate(n=Count("pk")).order_by():
        Collection.objects.filter(pk=row["collection_id"]).update(
            items_count=Greatest(F("items_count") - row["n"], 0)
        )
    items.delete()
    Favorite.objects.filter(**target).delete()
    Review.objects.filter(**target).delete()
    Download.objects.filter(**target).delete()
    from apps.translations.models import Translation

    Translation.objects.filter(**target).delete()


def recount_targets(targets: set[tuple[int, int]]) -> None:
    """Exact favorite and review counters of these (content type, id) pairs.

    For deletions that bypass the services, e.g. a player who deletes the account.
    """
    for content_type_id, object_id in targets:
        content_type = ContentType.objects.get_for_id(content_type_id)
        model = content_type.model_class()
        if model is None or not model._base_manager.filter(pk=object_id).exists():
            continue
        target = {"content_type_id": content_type_id, "object_id": object_id}
        model._base_manager.filter(pk=object_id).update(
            favorites_count=Favorite.objects.filter(**target).count()
        )
        recompute_rating(content_type=content_type, object_id=object_id)
