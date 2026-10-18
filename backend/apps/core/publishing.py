"""Status changes of player-made content (skins, servers, …) and the author's published count."""

from django.db import transaction
from django.utils import timezone

from .counters import bump
from .models import Publishable

#: A new author's first publications wait for a moderator
REVIEWED_FIRST = 3


def initial_status(author) -> str:
    """`pending` until the author has REVIEWED_FIRST published works (trusted roles skip it)."""
    if author.is_moderator or author.role == author.Role.TRUSTED:
        return Publishable.Status.PUBLISHED
    if author.published_count >= REVIEWED_FIRST:
        return Publishable.Status.PUBLISHED
    return Publishable.Status.PENDING


@transaction.atomic
def set_status(obj: Publishable, status: str, *, reason: str = "") -> None:
    """Moves `obj` to `status` and keeps `author.published_count` in step."""
    was_published = obj.status == Publishable.Status.PUBLISHED
    obj.status = status
    obj.rejection_reason = reason if status == Publishable.Status.REJECTED else ""
    fields = ["status", "rejection_reason"]
    if status == Publishable.Status.PUBLISHED and obj.published_at is None:
        obj.published_at = timezone.now()
        fields.append("published_at")
    obj.save(update_fields=fields)
    now_published = status == Publishable.Status.PUBLISHED
    if was_published != now_published:
        bump(obj.author, "published_count", 1 if now_published else -1)


def published_on_create(obj: Publishable) -> None:
    """Counts a work that was published right away (see initial_status)."""
    if obj.status == Publishable.Status.PUBLISHED:
        bump(obj.author, "published_count")


def withdrawn(obj: Publishable) -> None:
    """Call before deleting a work."""
    if obj.status == Publishable.Status.PUBLISHED:
        bump(obj.author, "published_count", -1)
