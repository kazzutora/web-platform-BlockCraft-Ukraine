import secrets

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models

from apps.core.models import Authored, Engagement, Publishable, TimeStamped

from .styles import ColorBucket, Style


def texture_upload_to(instance: "Skin", filename: str) -> str:
    return f"skins/{secrets.token_hex(8)}.png"


def preview_upload_to(instance: "Skin", filename: str) -> str:
    return f"skins/previews/{secrets.token_hex(8)}.png"


class Skin(TimeStamped, Authored, Publishable, Engagement):
    """A player-made skin: the 64×64 PNG texture plus what the catalog filters on."""

    class Model(models.TextChoices):
        CLASSIC = "classic", "Класична (Стів)"
        SLIM = "slim", "Тонкі руки (Алекс)"

    class Source(models.TextChoices):
        UPLOAD = "upload", "Завантажено"
        RECOLOR = "recolor", "Перефарбовано"

    title = models.CharField("назва", max_length=60)
    file = models.FileField("текстура", upload_to=texture_upload_to)
    preview = models.FileField("прев'ю", upload_to=preview_upload_to, blank=True)
    model = models.CharField("модель", max_length=8, choices=Model.choices)
    dominant_color = models.CharField("домінантний колір", max_length=7)
    color_bucket = models.CharField(
        "колір", max_length=8, choices=ColorBucket.choices, db_index=True
    )
    style_tags = ArrayField(
        models.CharField(max_length=16, choices=Style.choices), default=list, blank=True
    )
    source = models.CharField(max_length=8, choices=Source.choices, default=Source.UPLOAD)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="recolors"
    )
    #: SHA-256 of the normalized pixels: the same picture uploaded twice has the same hash
    texture_hash = models.CharField(max_length=64, db_index=True)
    #: The one skin the author shows in their profile
    is_current = models.BooleanField("поточний у профілі", default=False)

    class Meta:
        verbose_name = "скін"
        verbose_name_plural = "скіни"
        ordering = ["-created_at"]
        indexes = [
            GinIndex(fields=["style_tags"], name="skins_skin_styles_gin"),
            models.Index(fields=["status", "-published_at"], name="skins_skin_status_published"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["author"],
                condition=models.Q(is_current=True),
                name="skins_skin_one_current_per_author",
            )
        ]

    def __str__(self) -> str:
        return self.title
