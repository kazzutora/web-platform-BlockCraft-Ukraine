from django.core.files.base import ContentFile
from django.db import transaction

from apps.accounts.models import User
from apps.core.counters import bump
from apps.core.exceptions import DomainError

from . import textures
from .models import Skin

# Statuses in which the author may still show the skin in their profile
CURRENT_ALLOWED = {Skin.Status.PENDING, Skin.Status.PUBLISHED}


def render_preview(*, skin_id: int) -> bool:
    """Front view ×8 as PNG; safe to repeat. False when the skin is gone."""
    skin = Skin.objects.filter(pk=skin_id).first()
    if skin is None:
        return False
    with skin.file.open("rb") as file:
        image, _legacy = textures.load(file)
    previous = skin.preview.name if skin.preview else None
    preview = textures.render_front(image, skin.model)
    skin.preview.save("preview.png", ContentFile(textures.to_png(preview)), save=False)
    Skin.objects.filter(pk=skin.pk).update(preview=skin.preview.name)
    if previous:
        skin.preview.storage.delete(previous)
    return True


def record_download(*, skin: Skin) -> None:
    bump(skin, "downloads_count")


@transaction.atomic
def set_current(*, user: User, skin: Skin) -> Skin:
    """The one skin the player shows in their profile."""
    if skin.author_id != user.pk:
        raise DomainError(code="forbidden", message="Це не твій скін.", status=403)
    if skin.status not in CURRENT_ALLOWED:
        raise DomainError(code="skin_unavailable", message="Цей скін не можна показати в профілі.")
    Skin.objects.filter(author=user, is_current=True).exclude(pk=skin.pk).update(is_current=False)
    if not skin.is_current:
        skin.is_current = True
        skin.save(update_fields=["is_current"])
    return skin


def clear_current(*, user: User) -> None:
    Skin.objects.filter(author=user, is_current=True).update(is_current=False)
