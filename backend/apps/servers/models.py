import secrets
import string

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models import Q

from apps.core.models import Engagement, Sourced, SourcedQuerySet, TimeStamped

_CODE_ALPHABET = string.ascii_lowercase + string.digits
JAVA_PORT = 25565
BEDROCK_PORT = 19132


def new_verify_code() -> str:
    """Kept for migration 0001 only: codes are now per player (`services.claim_code`)."""
    return "bc-" + "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))


def banner_upload_to(instance: object, filename: str) -> str:
    """Kept for migration 0001 only: banners now come from the source as URLs."""
    return f"servers/banners/{secrets.token_hex(8)}.webp"


class ContentKind(models.TextChoices):
    VANILLA = "vanilla", "Без модів"
    MODDED = "modded", "З модами"


class ServerQuerySet(SourcedQuerySet):
    def listed(self):
        """What the catalog shows: from Modrinth, or added by an owner who proved the address."""
        return self.visible().filter(Q(source="modrinth") | Q(is_verified=True))


class Server(TimeStamped, Sourced, Engagement):
    """A real Minecraft server: mirrored from Modrinth or added by its owner (tech.md 6.5).

    `source=owner` keeps the normalized `host:port` in `external_id`, so one address is one
    server whichever way it came in.
    """

    name = models.CharField("назва", max_length=80)
    slug = models.SlugField(max_length=96, unique=True)
    java_host = models.CharField("адреса Java", max_length=253, blank=True)
    java_port = models.PositiveIntegerField("порт Java", default=JAVA_PORT)
    bedrock_host = models.CharField("адреса Bedrock", max_length=253, blank=True)
    bedrock_port = models.PositiveIntegerField("порт Bedrock", default=BEDROCK_PORT)
    #: ISO 3166-1 alpha-2; often unknown
    country = models.CharField("країна", max_length=2, blank=True, db_index=True)
    #: ISO 639-1 codes
    languages = ArrayField(models.CharField(max_length=8), default=list, blank=True)
    #: Modrinth server categories (modes and features)
    categories = ArrayField(models.CharField(max_length=48), default=list, blank=True)
    content_kind = models.CharField(
        "що потрібно", max_length=8, choices=ContentKind.choices, default=ContentKind.VANILLA
    )
    supported_versions = ArrayField(models.CharField(max_length=32), default=list, blank=True)
    recommended_version = models.CharField("рекомендована версія", max_length=32, blank=True)
    required_pack = models.ForeignKey(
        "packs.Pack",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="servers",
        verbose_name="збірка для входу",
    )
    #: The modpack Modrinth names for joining (its own project or the server's one);
    #: `required_pack` is imported from it by a task, the sync only remembers it
    modpack_project_id = models.CharField(max_length=16, blank=True)
    modpack_version_id = models.CharField(max_length=16, blank=True)
    summary = models.CharField("коротко", max_length=280, blank=True)
    description_html = models.TextField("опис (з джерела)", blank=True, editable=False)
    #: Written by the owner here, in Ukrainian (markdown → sanitized HTML)
    description_uk_md = models.TextField("опис українською", max_length=5000, blank=True)
    description_uk_html = models.TextField(blank=True, editable=False)
    icon_url = models.URLField(max_length=500, blank=True)
    banner_url = models.URLField(max_length=500, blank=True)
    discord_url = models.URLField(blank=True)
    website_url = models.URLField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="servers",
        verbose_name="власник",
    )
    #: The latest player who asked to own it (sees it before it is proven, gets it pinged);
    #: whoever puts their own code into the MOTD becomes `owner`
    claimant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="хоче стати власником",
    )
    claimed_at = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField("підтверджено", default=False)
    #: The owner chose the pack to join with: the sync leaves it (and «з модами») alone
    pack_chosen_by_owner = models.BooleanField(default=False)
    last_online_at = models.DateTimeField(null=True, blank=True, db_index=True)
    modrinth_plays = models.PositiveIntegerField("гравців за 2 тижні (Modrinth)", default=0)
    ip_copies_count = models.PositiveIntegerField(default=0)

    objects = ServerQuerySet.as_manager()

    class Meta(Sourced.Meta):
        verbose_name = "сервер"
        verbose_name_plural = "сервери"
        ordering = ["-created_at"]
        indexes = [
            GinIndex(fields=["languages"], name="servers_server_languages_gin"),
            GinIndex(fields=["categories"], name="servers_server_categories_gin"),
            GinIndex(fields=["supported_versions"], name="servers_server_versions_gin"),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def is_listed(self) -> bool:
        """In memory, the same rule as `Server.objects.listed()`."""
        return not self.is_hidden and (self.source == "modrinth" or self.is_verified)

    @property
    def address(self) -> str:
        """What players type in Minecraft: Java first; the port only when not the default."""
        if self.java_host:
            return _address(self.java_host, self.java_port, JAVA_PORT)
        return _address(self.bedrock_host, self.bedrock_port, BEDROCK_PORT)

    @property
    def edition(self) -> str:
        if self.java_host and self.bedrock_host:
            return "both"
        return "java" if self.java_host else "bedrock"


def _address(host: str, port: int, default: int) -> str:
    host = f"[{host}]" if ":" in host else host
    return host if port == default else f"{host}:{port}"


class ServerSnapshot(models.Model):
    """One ping (every 5 minutes); raw rows live 30 days."""

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
