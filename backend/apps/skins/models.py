import secrets

from django.conf import settings
from django.db import models

from apps.core.models import Engagement, Sourced, TimeStamped

from .styles import ColorBucket


def texture_upload_to(instance: "Skin", filename: str) -> str:
    return f"skins/{secrets.token_hex(8)}.png"


def preview_upload_to(instance: "Skin", filename: str) -> str:
    return f"skins/previews/{secrets.token_hex(8)}.png"


class Skin(TimeStamped, Sourced, Engagement):
    """A real skin from MineSkin's public gallery or a player's skin via Mojang (tech.md 6.6).

    `external_id`: the MineSkin uuid, or the textures.minecraft.net id for Mojang. The same
    picture never comes twice: `texture_hash` (SHA-256 of the pixels) is unique, the first
    source wins.
    """

    class Model(models.TextChoices):
        CLASSIC = "classic", "Класична (Стів)"
        SLIM = "slim", "Тонкі руки (Алекс)"

    title = models.CharField("назва", max_length=80)
    #: The cached 64×64 PNG (legacy 64×32 textures are converted)
    texture = models.FileField("текстура", upload_to=texture_upload_to)
    #: Where the texture lives at the source (textures.minecraft.net)
    texture_url = models.URLField("текстура в джерелі", max_length=300, blank=True)
    texture_hash = models.CharField(max_length=64, unique=True)
    preview = models.FileField("прев'ю", upload_to=preview_upload_to, blank=True)
    model = models.CharField("модель", max_length=8, choices=Model.choices)
    dominant_color = models.CharField("домінантний колір", max_length=7)
    color_bucket = models.CharField(
        "колір", max_length=8, choices=ColorBucket.choices, db_index=True
    )
    #: The Minecraft nickname, for skins found by nickname (Mojang)
    player_name = models.CharField("нік гравця", max_length=16, blank=True)
    #: Views on MineSkin, when known
    source_views = models.PositiveIntegerField(default=0)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="added_skins",
        verbose_name="додав",
    )

    class Meta(Sourced.Meta):
        verbose_name = "скін"
        verbose_name_plural = "скіни"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_hidden", "-created_at"], name="skins_skin_visible_new"),
        ]

    def __str__(self) -> str:
        return self.title
