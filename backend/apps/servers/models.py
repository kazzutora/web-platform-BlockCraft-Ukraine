import secrets
import string

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models

from apps.core.models import Authored, Engagement, Publishable, TimeStamped

from .choices import Edition, Language, Mode

_CODE_ALPHABET = string.ascii_lowercase + string.digits


def new_verify_code() -> str:
    return "bc-" + "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))


def banner_upload_to(instance: "Server", filename: str) -> str:
    return f"servers/banners/{secrets.token_hex(8)}.webp"


class Server(TimeStamped, Authored, Publishable, Engagement):
    """A Minecraft server players can join; the author is its owner."""

    name = models.CharField("назва", max_length=60)
    slug = models.SlugField(max_length=64, unique=True)
    host = models.CharField("адреса", max_length=253)
    port = models.PositiveIntegerField("порт", default=25565)
    edition = models.CharField("видання", max_length=8, choices=Edition.choices)
    modes = ArrayField(models.CharField(max_length=16, choices=Mode.choices), default=list)
    versions_label = models.CharField("версії", max_length=32, blank=True)
    language = models.CharField("мова", max_length=8, choices=Language.choices)
    description = models.TextField("опис", max_length=500, blank=True)
    banner = models.ImageField("банер", upload_to=banner_upload_to, blank=True)
    discord_url = models.URLField(blank=True)
    website_url = models.URLField(blank=True)
    has_whitelist = models.BooleanField("вайтліст", default=False)
    is_verified = models.BooleanField("перевірено", default=False)
    verify_code = models.CharField(max_length=16, default=new_verify_code, editable=False)
    last_online_at = models.DateTimeField(null=True, blank=True)
    ip_copies_count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "сервер"
        verbose_name_plural = "сервери"
        ordering = ["-created_at"]
        indexes = [
            GinIndex(fields=["modes"], name="servers_server_modes_gin"),
            models.Index(fields=["status", "-published_at"], name="servers_server_status_pub"),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def address(self) -> str:
        """What players type in Minecraft: the port only when it is not the default one."""
        default = 19132 if self.edition == Edition.BEDROCK else 25565
        host = f"[{self.host}]" if ":" in self.host else self.host
        return host if self.port == default else f"{host}:{self.port}"


class ServerSnapshot(models.Model):
    """One ping (every 5 minutes); raw rows live 30 days (stage 17 aggregates them)."""

    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name="snapshots")
    ts = models.DateTimeField(db_index=True)
    is_online = models.BooleanField()
    players_online = models.PositiveIntegerField(default=0)
    players_max = models.PositiveIntegerField(default=0)
    latency_ms = models.PositiveIntegerField(null=True)
    version_name = models.CharField(max_length=64, blank=True)

    class Meta:
        verbose_name = "знімок онлайну"
        verbose_name_plural = "знімки онлайну"
        indexes = [models.Index(fields=["server", "-ts"], name="servers_snapshot_server_ts")]

    def __str__(self) -> str:
        return f"{self.server_id} @ {self.ts:%Y-%m-%d %H:%M}"
