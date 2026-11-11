import secrets

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
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
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name="items")
    position = models.PositiveIntegerField(default=0)
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
    """«Взяв»: a signed-in player took something (a file, a .mrpack, an address, a PNG).

    Feeds «Взяв» in /me and the trends; guests only move the counters (tech.md 6.7).
    """

    class Action(models.TextChoices):
        DOWNLOAD = "download", "Завантажив файл"
        EXPORT_MRPACK = "export_mrpack", "Завантажив .mrpack"
        COPY_IP = "copy_ip", "Скопіював IP"
        DOWNLOAD_PNG = "download_png", "Завантажив PNG"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="downloads"
    )
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="+", null=True
    )
    object_id = models.PositiveBigIntegerField(null=True)
    target = GenericForeignKey("content_type", "object_id")
    action = models.CharField(max_length=16, choices=Action.choices, default=Action.DOWNLOAD)
    #: For mods: the project and the exact file (trends count projects)
    project = models.ForeignKey(
        "mods.Project",
        on_delete=models.CASCADE,
        related_name="user_downloads",
        null=True,
        blank=True,
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
        indexes = [
            models.Index(fields=["user", "project"], name="library_download_user_proj"),
            models.Index(fields=["user", "-created_at"], name="library_download_user_new"),
            models.Index(fields=["content_type", "object_id"], name="library_download_target"),
        ]

    def __str__(self) -> str:
        return f"{self.user} ← {self.content_type_id}#{self.object_id}"
