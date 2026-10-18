import secrets
from io import BytesIO
from typing import Any

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from PIL import Image, ImageOps, UnidentifiedImageError

from apps.core.exceptions import DomainError

from .models import GameProfile, User, UserSettings

AVATAR_SIZE = 256
AVATAR_MAX_BYTES = 2 * 1024 * 1024
AVATAR_FORMATS = {"PNG", "JPEG", "WEBP", "GIF"}


@transaction.atomic
def ensure_profiles(*, user: User) -> None:
    """Every user has a game profile and settings; called right after the user is created."""
    GameProfile.objects.get_or_create(user=user)
    UserSettings.objects.get_or_create(user=user)


def _apply(instance: Any, data: dict[str, Any], allowed: set[str]) -> list[str]:
    changed = [name for name in data if name in allowed]
    for name in changed:
        setattr(instance, name, data[name])
    return changed


def update_account(*, user: User, data: dict[str, Any]) -> User:
    changed = _apply(user, data, {"bio", "mc_nickname", "is_private"})
    if changed:
        user.save(update_fields=changed)
    return user


def update_game_profile(*, user: User, data: dict[str, Any]) -> GameProfile:
    profile = user.game_profile
    changed = _apply(profile, data, {"game_version", "loader", "edition", "interests"})
    if changed:
        profile.save(update_fields=changed)
    return profile


def complete_onboarding(*, user: User, data: dict[str, Any]) -> GameProfile:
    """Saves what the player chose on /welcome; skipping leaves the fields empty."""
    profile = user.game_profile
    changed = _apply(profile, data, {"game_version", "loader", "edition", "interests"})
    profile.onboarding_done = True
    profile.save(update_fields=[*changed, "onboarding_done"])
    return profile


def update_settings(*, user: User, data: dict[str, Any]) -> UserSettings:
    settings = user.settings
    changed = _apply(
        settings,
        data,
        {
            "theme",
            "language",
            "notify_prefs",
            "history_enabled",
            "who_can_comment",
            "collections_visible",
        },
    )
    if changed:
        settings.save(update_fields=changed)
    return settings


def _square_webp(upload: UploadedFile) -> ContentFile:
    if upload.size and upload.size > AVATAR_MAX_BYTES:
        raise DomainError(
            code="avatar_too_large",
            message="Аватар має бути до 2 МБ.",
            fields={"avatar": ["Аватар має бути до 2 МБ."]},
        )
    try:
        image = Image.open(upload)
        image_format = image.format
        image.load()
    except (UnidentifiedImageError, OSError) as error:
        raise DomainError(
            code="avatar_invalid",
            message="Це не схоже на зображення.",
            fields={"avatar": ["Завантаж PNG, JPEG, WebP або GIF."]},
        ) from error
    if image_format not in AVATAR_FORMATS:
        raise DomainError(
            code="avatar_invalid",
            message="Непідтримуваний формат зображення.",
            fields={"avatar": ["Завантаж PNG, JPEG, WebP або GIF."]},
        )

    image = ImageOps.exif_transpose(image).convert("RGBA")
    image = ImageOps.fit(image, (AVATAR_SIZE, AVATAR_SIZE), Image.Resampling.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, format="WEBP", quality=85)
    return ContentFile(buffer.getvalue(), name=f"avatar-{secrets.token_hex(6)}.webp")


def set_avatar(*, user: User, upload: UploadedFile) -> User:
    content = _square_webp(upload)
    previous = user.avatar.name if user.avatar else None
    user.avatar.save(content.name, content, save=False)
    user.save(update_fields=["avatar"])
    if previous:
        user.avatar.storage.delete(previous)
    return user


def remove_avatar(*, user: User) -> User:
    if user.avatar:
        user.avatar.delete(save=False)
        user.save(update_fields=["avatar"])
    return user
