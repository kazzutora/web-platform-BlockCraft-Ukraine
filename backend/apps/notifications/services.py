from django.db.models import Model

from apps.accounts.models import User
from apps.core import kinds

from .models import Notification

EXCERPT_LENGTH = 120


def notify(*, user: User | None, type: str, target: Model | None = None, **payload) -> None:
    """Saves a notification unless the player switched this type off in the settings."""
    if user is None or not user.is_active:
        return
    prefs = getattr(getattr(user, "settings", None), "notify_prefs", None) or {}
    if prefs.get(type) is False:
        return
    if target is not None:
        payload = {**about(target), **payload}
    if "excerpt" in payload:
        payload["excerpt"] = payload["excerpt"][:EXCERPT_LENGTH]
    Notification.objects.create(user=user, type=type, payload=payload)


def about(target: Model) -> dict:
    """What the text and the link need; a review points at what it reviews."""
    from apps.social.models import Review

    if isinstance(target, Review):
        reviewed = about(target.target) if target.target is not None else {}
        return {**reviewed, "excerpt": target.text, "review": target.pk}
    kind = kinds.kind_for_model(type_of(target))
    title = getattr(target, "title", None) or getattr(target, "name", "")
    return {"kind": kind.name, "id": kind.identifier(target), "title": title}


def type_of(obj: Model) -> type[Model]:
    return obj._meta.model


def unread_count(user: User) -> int:
    return Notification.objects.filter(user=user, is_read=False).count()


def mark_read(*, user: User, ids: list[int] | None = None) -> int:
    queryset = Notification.objects.filter(user=user, is_read=False)
    if ids:
        queryset = queryset.filter(pk__in=ids)
    return queryset.update(is_read=True)
