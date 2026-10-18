from collections.abc import Iterable

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.core import publishing
from apps.core.counters import bump
from apps.core.exceptions import DomainError
from apps.moderation import services as moderation
from apps.moderation import words

from . import textures
from .models import Skin
from .styles import MAX_STYLES

# Statuses in which the author may still show the skin in their profile
CURRENT_ALLOWED = {Skin.Status.PENDING, Skin.Status.PUBLISHED}


def _texture_error(error: textures.SkinTextureError) -> DomainError:
    return DomainError(code=error.code, message=error.message, fields={"file": [error.message]})


def clean_styles(style_tags: Iterable[str]) -> list[str]:
    unique = list(dict.fromkeys(style_tags))
    if len(unique) > MAX_STYLES:
        message = f"Обери до {MAX_STYLES} стилів."
        raise DomainError(code="too_many_styles", message=message, fields={"style_tags": [message]})
    return unique


def _check_author(skin: Skin, user: User) -> None:
    if skin.author_id != user.pk and not user.is_moderator:
        raise DomainError(code="forbidden", message="Це не твій скін.", status=403)


def _queue_preview(skin: Skin) -> None:
    from . import tasks

    transaction.on_commit(lambda: tasks.render_preview.delay(skin.pk))


@transaction.atomic
def upload_skin(
    *,
    author: User,
    upload: UploadedFile,
    title: str,
    style_tags: Iterable[str] = (),
    model: str = "",
) -> Skin:
    """Checks the PNG, detects model and colour; the 2D preview is rendered in Celery."""
    moderation.ensure_can_publish(author)
    words.check(title=title)
    try:
        analysis = textures.analyse(upload, size=upload.size, model=model)
    except textures.SkinTextureError as error:
        raise _texture_error(error) from error
    if Skin.objects.filter(author=author, texture_hash=analysis.texture_hash).exists():
        message = "Цей скін уже є серед твоїх."
        raise DomainError(code="skin_duplicate", message=message, fields={"file": [message]})

    status = publishing.initial_status(author)
    skin = Skin(
        author=author,
        title=title.strip(),
        model=analysis.model,
        dominant_color=analysis.dominant_color,
        color_bucket=analysis.color_bucket,
        style_tags=clean_styles(style_tags),
        texture_hash=analysis.texture_hash,
        status=status,
        published_at=timezone.now() if status == Skin.Status.PUBLISHED else None,
    )
    skin.file.save("skin.png", ContentFile(textures.to_png(analysis.image)), save=False)
    skin.save()
    publishing.published_on_create(skin)
    _queue_preview(skin)
    return skin


@transaction.atomic
def update_skin(
    *,
    skin: Skin,
    user: User,
    title: str | None = None,
    style_tags: Iterable[str] | None = None,
    model: str | None = None,
) -> Skin:
    _check_author(skin, user)
    fields = ["updated_at"]
    if title is not None:
        words.check(title=title)
        skin.title = title.strip()
        fields.append("title")
    if style_tags is not None:
        skin.style_tags = clean_styles(style_tags)
        fields.append("style_tags")
    if model is not None and model != skin.model:
        # Arm width changes what the front looks like: colour and preview follow
        with skin.file.open("rb") as file:
            analysis = textures.analyse(file, model=model)
        skin.model = analysis.model
        skin.dominant_color = analysis.dominant_color
        skin.color_bucket = analysis.color_bucket
        fields += ["model", "dominant_color", "color_bucket"]
        _queue_preview(skin)
    skin.save(update_fields=fields)
    return skin


@transaction.atomic
def delete_skin(*, skin: Skin, user: User) -> None:
    _check_author(skin, user)
    publishing.withdrawn(skin)
    files = [field.name for field in (skin.file, skin.preview) if field]
    storage = skin.file.storage
    skin.delete()
    transaction.on_commit(lambda: [storage.delete(name) for name in files])


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


# Moderation (admin actions until stage 8)


def approve(*, skin: Skin, moderator: User | None = None) -> Skin:
    moderation.approve(obj=skin, moderator=moderator)
    return skin


def reject(*, skin: Skin, reason: str, moderator: User | None = None) -> Skin:
    moderation.reject(obj=skin, reason=reason, moderator=moderator)
    if skin.is_current:
        skin.is_current = False
        skin.save(update_fields=["is_current"])
    return skin
