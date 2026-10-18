from collections import defaultdict
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Avg, Count, F, FloatField, Func, Model, QuerySet, Sum
from django.db.models.functions import Exp, Greatest
from django.utils import timezone

from apps.accounts.models import User, UserSettings
from apps.core import kinds
from apps.core.counters import bump
from apps.core.exceptions import DomainError
from apps.library.models import Collection, CollectionItem, Download, Favorite
from apps.moderation import services as moderation
from apps.moderation import words
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import Comment, Like, Review, ReviewVote

BAYES_WEIGHT = 10  # C in score = (C·m + Σstars) / (C + n)


# Likes


@transaction.atomic
def like(*, user: User, kind: str, identifier: str) -> tuple[kinds.Kind, Model]:
    kind_obj, target = kinds.resolve(kind, identifier, viewer=user, action="like")
    _, created = Like.objects.get_or_create(
        user=user, content_type=kind_obj.content_type, object_id=target.pk
    )
    if created:
        bump(target, "likes_count", 1)
    return kind_obj, target


@transaction.atomic
def unlike(*, user: User, kind: str, identifier: str) -> tuple[kinds.Kind, Model]:
    kind_obj, target = kinds.resolve(kind, identifier, viewer=user, action="like")
    deleted, _ = Like.objects.filter(
        user=user, content_type=kind_obj.content_type, object_id=target.pk
    ).delete()
    if deleted:
        bump(target, "likes_count", -1)
    return kind_obj, target


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
    if created:
        notify(
            user=owner,
            type=Notification.Type.REVIEW,
            target=target,
            actor=user.nickname,
            excerpt=review.text,
        )
    return review, created


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
    """Bayesian average for review kinds, likes for like kinds; stored in `score`."""
    updated: dict[str, int] = {}
    for kind in kinds.all_kinds():
        model = kind.model
        if kind.rating == "like":
            updated[kind.name] = model._base_manager.update(score=F("likes_count"))
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
TREND_WEIGHTS = {"like": 1.0, "favorite": 2.0, "download": 0.5, "review": 3.0}


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
    """Recent likes, saves, downloads and reviews; older events fade out."""
    now = now or timezone.now()
    updated: dict[str, int] = {}
    for kind in kinds.all_kinds():
        target = {"content_type": kind.content_type}
        trends: dict[int, float] = defaultdict(float)
        sources = [
            (Like.objects.filter(**target), "object_id", TREND_WEIGHTS["like"]),
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


# Comments


def comment_owner(kind: kinds.Kind, target: Model) -> User | None:
    return kind.owner_of(target)


def can_comment(*, user: User, kind: kinds.Kind, target: Model) -> bool:
    """The owner's «who can comment» applies; followers arrive in stage 14 (until then: nobody)."""
    if not user.is_authenticated:
        return False
    owner = comment_owner(kind, target)
    if owner is None or owner.pk == user.pk or user.is_moderator:
        return True
    policy = (
        UserSettings.objects.filter(user=owner).values_list("who_can_comment", flat=True).first()
    )
    return policy in (None, UserSettings.CommentPolicy.ALL)


@transaction.atomic
def add_comment(
    *, user: User, kind: str, identifier: str, body: str, parent_id: int | None = None
) -> Comment:
    kind_obj, target = kinds.resolve(kind, identifier, viewer=user, action="comment")
    if not can_comment(user=user, kind=kind_obj, target=target):
        raise DomainError(code="comments_closed", message="Автор закрив коментарі.", status=403)
    moderation.ensure_can_publish(user)
    words.check(body=body)
    parent = None
    if parent_id is not None:
        parent = Comment.objects.filter(
            pk=parent_id,
            content_type=kind_obj.content_type,
            object_id=target.pk,
            parent__isnull=True,
            is_deleted=False,
        ).first()
        if parent is None:
            raise DomainError(
                code="invalid_parent",
                message="Відповідати можна лише на коментарі першого рівня.",
                fields={"parent": ["Відповідати можна лише на коментарі першого рівня."]},
            )
    comment = Comment.objects.create(
        user=user,
        content_type=kind_obj.content_type,
        object_id=target.pk,
        parent=parent,
        body=body.strip(),
        status=Comment.Status.PUBLISHED,
    )
    bump(target, "comments_count", 1)
    if parent is not None and parent.user_id != user.pk:
        notify(
            user=parent.user,
            type=Notification.Type.REPLY,
            target=target,
            actor=user.nickname,
            excerpt=comment.body,
        )
    return comment


def edit_comment(*, comment: Comment, user: User, body: str) -> Comment:
    if comment.user_id != user.pk or comment.is_deleted:
        raise DomainError(
            code="forbidden", message="Редагувати можна лише свій коментар.", status=403
        )
    words.check(body=body)
    comment.body = body.strip()
    comment.save(update_fields=["body", "updated_at"])
    return comment


def _target_of(comment: Comment) -> tuple[kinds.Kind, Model]:
    kind = kinds.kind_for_content_type(comment.content_type_id)
    return kind, kind.model._base_manager.get(pk=comment.object_id)


@transaction.atomic
def delete_comment(*, comment: Comment, user: User) -> None:
    """Author, target owner or moderator. A comment with replies stays as «видалено»."""
    kind, target = _target_of(comment)
    owner = comment_owner(kind, target)
    if (
        comment.user_id != user.pk
        and not user.is_moderator
        and getattr(owner, "pk", None) != user.pk
    ):
        raise DomainError(code="forbidden", message="Видалити цей коментар не можна.", status=403)
    if comment.parent_id is None and comment.replies.exists():
        comment.is_deleted = True
        comment.is_pinned = False
        comment.body = ""
        comment.save(update_fields=["is_deleted", "is_pinned", "body", "updated_at"])
    else:
        comment.delete()
    bump(target, "comments_count", -1)


@transaction.atomic
def toggle_pin(*, comment: Comment, user: User) -> Comment:
    """The target owner (or a moderator) pins one top-level comment."""
    kind, target = _target_of(comment)
    owner = comment_owner(kind, target)
    if getattr(owner, "pk", None) != user.pk and not user.is_moderator:
        raise DomainError(code="forbidden", message="Закріплювати може лише автор.", status=403)
    if comment.parent_id is not None or comment.is_deleted:
        raise DomainError(
            code="invalid_pin", message="Закріпити можна лише коментар першого рівня."
        )
    pinned = not comment.is_pinned
    if pinned:
        Comment.objects.filter(
            content_type=comment.content_type, object_id=comment.object_id, is_pinned=True
        ).update(is_pinned=False)
    comment.is_pinned = pinned
    comment.save(update_fields=["is_pinned"])
    return comment


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
    Like.objects.filter(**target).delete()
    Review.objects.filter(**target).delete()
    Comment.objects.filter(**target).delete()


def recount_targets(targets: set[tuple[int, int]]) -> None:
    """Exact favorite, like, comment and review counters of these (content type, id) pairs.

    For deletions that bypass the services, e.g. a player who deletes the account.
    """
    for content_type_id, object_id in targets:
        content_type = ContentType.objects.get_for_id(content_type_id)
        model = content_type.model_class()
        if model is None or not model._base_manager.filter(pk=object_id).exists():
            continue
        target = {"content_type_id": content_type_id, "object_id": object_id}
        model._base_manager.filter(pk=object_id).update(
            favorites_count=Favorite.objects.filter(**target).count(),
            likes_count=Like.objects.filter(**target).count(),
            comments_count=Comment.objects.filter(
                **target, status=Comment.Status.PUBLISHED, is_deleted=False
            ).count(),
        )
        recompute_rating(content_type=content_type, object_id=object_id)
