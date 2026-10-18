from collections.abc import Iterable

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django.db.models import Model, Q
from django.http import Http404
from django.utils import timezone

from apps.accounts.models import User
from apps.core import kinds, publishing
from apps.core.exceptions import DomainError
from apps.core.models import Publishable
from apps.library.models import Collection
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.social.models import Comment

from .models import Report, Sanction

AUTO_HIDE_REPORTS = 5
TRUSTED_AFTER = publishing.REVIEWED_FIRST


# What can be reported


def resolve_target(*, kind: str, identifier: str, viewer: User) -> Model:
    """A visible object of a kind that allows reports, or a published comment."""
    if kind == "comment":
        if not identifier.isdigit():
            raise Http404
        comment = Comment.objects.filter(
            pk=identifier, status=Comment.Status.PUBLISHED, is_deleted=False
        ).first()
        if comment is None:
            raise Http404
        return comment
    _, target = kinds.resolve(kind, identifier, viewer=viewer, action="report")
    return target


def author_of(target: Model) -> User | None:
    if isinstance(target, Comment):
        return target.user
    if isinstance(target, Collection):
        return target.owner
    return getattr(target, "author", None) or getattr(target, "claimed_by", None)


def _set_visible(target: Model, visible: bool) -> None:
    """Saved through `save()`: the search index hears about it (signals)."""
    if isinstance(target, Collection):
        target.visibility = (
            Collection.Visibility.PUBLIC if visible else Collection.Visibility.PRIVATE
        )
        target.save(update_fields=["visibility", "updated_at"])
        return
    status = Publishable.Status.PUBLISHED if visible else Publishable.Status.HIDDEN
    if hasattr(target, "author_id"):
        publishing.set_status(target, status)  # keeps the author's published count
    else:
        target.status = status
        target.save(update_fields=["status"])


def _hide(target: Model) -> None:
    _set_visible(target, False)


def _restore(target: Model) -> None:
    _set_visible(target, True)


# Reports


def _open_reports(target: Model):
    return Report.objects.filter(
        content_type=ContentType.objects.get_for_model(target),
        object_id=target.pk,
        status=Report.Status.NEW,
    )


@transaction.atomic
def report(*, reporter: User, kind: str, identifier: str, reason: str, comment: str = "") -> Report:
    """A player's report; the fifth independent one hides the object until a moderator decides."""
    target = resolve_target(kind=kind, identifier=identifier, viewer=reporter)
    if author_of(target) == reporter:
        raise DomainError(code="own_object", message="На свою роботу скаржитися не можна.")
    try:
        with transaction.atomic():
            created = Report.objects.create(
                reporter=reporter,
                content_type=ContentType.objects.get_for_model(target),
                object_id=target.pk,
                reason=reason,
                comment=comment.strip(),
            )
    except IntegrityError as error:
        raise DomainError(
            code="already_reported", message="Ти вже поскаржився — модератори розглянуть."
        ) from error
    open_reports = _open_reports(target)
    if open_reports.values("reporter").distinct().count() >= AUTO_HIDE_REPORTS:
        if not open_reports.filter(auto_hidden=True).exists():
            _hide(target)
        open_reports.update(auto_hidden=True)
    return created


def _targets(reports: Iterable[Report]) -> dict[tuple[int, int], Model]:
    found = {}
    for item in reports:
        key = (item.content_type_id, item.object_id)
        if key not in found and item.target is not None:
            found[key] = item.target
    return found


@transaction.atomic
def accept_reports(*, reports: Iterable[Report], moderator: User | None) -> int:
    """The moderator agrees: the object is hidden, all its open reports close, the author learns."""
    targets = _targets(reports)
    for target in targets.values():
        open_reports = _open_reports(target)
        if not open_reports.filter(auto_hidden=True).exists():
            _hide(target)
        open_reports.update(
            status=Report.Status.ACCEPTED, handled_by=moderator, handled_at=timezone.now()
        )
        extra = {"excerpt": target.body} if isinstance(target, Comment) else {}
        notify(
            user=author_of(target),
            type=Notification.Type.HIDDEN,
            target=_link_target(target),
            **extra,
        )
    return len(targets)


@transaction.atomic
def reject_reports(*, reports: Iterable[Report], moderator: User | None) -> int:
    """Nothing wrong: open reports close and an automatically hidden object comes back."""
    targets = _targets(reports)
    for target in targets.values():
        open_reports = _open_reports(target)
        if open_reports.filter(auto_hidden=True).exists():
            _restore(target)
            notify(
                user=author_of(target), type=Notification.Type.RESTORED, target=_link_target(target)
            )
        open_reports.update(
            status=Report.Status.REJECTED, handled_by=moderator, handled_at=timezone.now()
        )
    return len(targets)


def _link_target(target: Model) -> Model | None:
    """Notifications link to a kind object; for a comment — to what it was written under."""
    return target.target if isinstance(target, Comment) else target


# Publications (skins, servers): the first three of a new author wait for a moderator


@transaction.atomic
def approve(*, obj: Model, moderator: User | None = None) -> Model:
    publishing.set_status(obj, Publishable.Status.PUBLISHED)
    author = obj.author
    author.refresh_from_db(fields=["published_count", "role"])
    if author.role == User.Role.USER and author.published_count >= TRUSTED_AFTER:
        author.role = User.Role.TRUSTED
        author.save(update_fields=["role"])
    notify(user=author, type=Notification.Type.APPROVED, target=obj)
    return obj


@transaction.atomic
def reject(*, obj: Model, reason: str, moderator: User | None = None) -> Model:
    publishing.set_status(obj, Publishable.Status.REJECTED, reason=reason)
    notify(user=obj.author, type=Notification.Type.REJECTED, target=obj, reason=reason)
    return obj


# Sanctions


def active_sanctions(user: User, *types: str):
    now = timezone.now()
    return Sanction.objects.filter(user=user, type__in=types).filter(
        Q(until__isnull=True) | Q(until__gt=now)
    )


def ensure_can_publish(user: User) -> None:
    """Called before uploads, servers, comments and reviews."""
    if active_sanctions(user, Sanction.Type.PUBLISH_BAN, Sanction.Type.BAN).exists():
        raise DomainError(
            code="publish_banned",
            message="Публікації для тебе тимчасово закриті рішенням модераторів.",
            status=403,
        )


@transaction.atomic
def issue_sanction(
    *, user: User, type: str, reason: str, until=None, moderator: User | None = None
) -> Sanction:
    sanction = Sanction.objects.create(
        user=user, type=type, reason=reason, until=until, issued_by=moderator
    )
    if type == Sanction.Type.BAN:
        # An inactive user is no longer loaded from the session: the ban works at once
        User.objects.filter(pk=user.pk).update(is_active=False)
    else:
        notify(user=user, type=Notification.Type.WARNING, reason=reason)
    return sanction


def lift_expired_bans() -> int:
    """Hourly: a ban that ran out lets the player back in, unless another one is still on."""
    now = timezone.now()
    expired = Sanction.objects.filter(type=Sanction.Type.BAN, until__lte=now).values("user")
    lifted = 0
    for user in User.objects.filter(pk__in=expired, is_active=False):
        if not active_sanctions(user, Sanction.Type.BAN).exists():
            User.objects.filter(pk=user.pk).update(is_active=True)
            lifted += 1
    return lifted
