import secrets

from django.conf import settings
from django.db import models

from apps.core.models import Engagement, GenericTarget, TimeStamped


class Favorite(GenericTarget):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "обране"
        verbose_name_plural = "обране"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "content_type", "object_id"], name="library_favorite_unique"
            )
        ]
        indexes = [models.Index(fields=["content_type", "object_id"], name="library_fav_target")]

    def __str__(self) -> str:
        return f"{self.user} ♥ {self.content_type.model}#{self.object_id}"


def new_share_token() -> str:
    return secrets.token_urlsafe(12)


class Collection(TimeStamped, Engagement):
    class Visibility(models.TextChoices):
        PRIVATE = "private", "Лише я"
        LINK = "link", "За посиланням"
        PUBLIC = "public", "Усі"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="collections"
    )
    title = models.CharField("назва", max_length=80)
    description = models.CharField("опис", max_length=200, blank=True)
    visibility = models.CharField(
        max_length=8, choices=Visibility.choices, default=Visibility.PRIVATE, db_index=True
    )
    share_token = models.CharField(max_length=32, unique=True, default=new_share_token)
    is_setup = models.BooleanField(default=False)
    editors = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="editable_collections"
    )
    copied_from = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="copies"
    )
    items_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "колекція"
        verbose_name_plural = "колекції"
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.title


class CollectionItem(GenericTarget):
    class Slot(models.TextChoices):
        VERSION = "version", "Версія"
        LOADER = "loader", "Лоадер"
        PACK = "pack", "Зборка"
        MOD = "mod", "Мод"
        RESOURCEPACK = "resourcepack", "Ресурспак"
        SHADER = "shader", "Шейдер"
        SKIN = "skin", "Скін"
        SERVER = "server", "Сервер"

    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name="items")
    position = models.PositiveIntegerField(default=0)
    slot = models.CharField(max_length=16, choices=Slot.choices, blank=True)
    note = models.CharField("нотатка", max_length=140, blank=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "елемент колекції"
        verbose_name_plural = "елементи колекції"
        ordering = ["position", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["collection", "content_type", "object_id"], name="library_item_unique"
            )
        ]
        indexes = [models.Index(fields=["content_type", "object_id"], name="library_item_target")]

    def __str__(self) -> str:
        return f"{self.collection} · {self.content_type.model}#{self.object_id}"


class Download(models.Model):
    """A signed-in user took a file; used later to track updates of what they installed."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="downloads"
    )
    project = models.ForeignKey(
        "mods.Project", on_delete=models.CASCADE, related_name="user_downloads"
    )
    version = models.ForeignKey(
        "mods.ProjectVersion", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    game_version = models.CharField(max_length=32, blank=True)
    loader = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "завантаження"
        verbose_name_plural = "завантаження"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "project"], name="library_download_user_proj")]

    def __str__(self) -> str:
        return f"{self.user} ← {self.project}"
