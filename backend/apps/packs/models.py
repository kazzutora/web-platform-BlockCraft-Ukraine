import secrets

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q

from apps.core.models import Authored, Engagement, Publishable, TimeStamped

from .choices import PackLoader


def cover_upload_to(instance: "Pack", filename: str) -> str:
    return f"packs/covers/{secrets.token_hex(8)}.webp"


def new_share_token() -> str:
    return secrets.token_urlsafe(12)[:16]


class Origin(models.TextChoices):
    #: A popular modpack mirrored from Modrinth: players download the original .mrpack
    MODRINTH = "modrinth", "Modrinth"
    #: Put together here by a player from real catalog projects
    COMMUNITY = "community", "Спільнота"


class Visibility(models.TextChoices):
    PRIVATE = "private", "Лише я"
    LINK = "link", "За посиланням"
    PUBLIC = "public", "Усім"


class CompatStatus(models.TextChoices):
    OK = "ok", "Сумісно"
    WARNINGS = "warnings", "Є попередження"
    ERRORS = "errors", "Є проблеми"
    UNKNOWN = "unknown", "Не перевірено"


class Pack(TimeStamped, Authored, Publishable, Engagement):
    """A set of mods, resource packs and shaders for one game version and loader.

    Files stay on Modrinth: the pack keeps references to versions, `.mrpack` links to them.
    `compat_report` is the last `Resolution` of the set (apps/compat), kept until it changes.
    """

    origin = models.CharField(
        "звідки", max_length=16, choices=Origin.choices, default=Origin.COMMUNITY, db_index=True
    )
    title = models.CharField("назва", max_length=80)
    slug = models.SlugField(max_length=96, unique=True)
    #: A mosaic of the first item icons, drawn by `packs.render_cover`; players upload nothing
    cover = models.ImageField("обкладинка", upload_to=cover_upload_to, blank=True)
    summary = models.CharField("коротко", max_length=280, blank=True)
    description_html = models.TextField("опис (з Modrinth)", blank=True, editable=False)
    # A supported sources.GameVersion; packs keep the string to survive version cleanups
    game_version = models.CharField("версія гри", max_length=32)
    loader = models.CharField("лоадер", max_length=16, choices=PackLoader.choices)
    #: Pinned by the author; empty — the latest stable one we know (see LoaderRelease)
    loader_version = models.CharField("версія лоадера", max_length=64, blank=True)
    items_count = models.PositiveIntegerField("елементів", default=0)
    compat_status = models.CharField(
        "сумісність", max_length=8, choices=CompatStatus.choices, default=CompatStatus.UNKNOWN
    )
    compat_checked_at = models.DateTimeField("перевірено", null=True, blank=True)
    compat_report = models.JSONField("звіт сумісності", default=dict, blank=True)

    # Community packs
    visibility = models.CharField(
        "видимість", max_length=8, choices=Visibility.choices, default=Visibility.PUBLIC
    )
    share_token = models.CharField(max_length=16, default=new_share_token, editable=False)
    ram_min_gb = models.PositiveSmallIntegerField("мінімум RAM, ГБ", default=4)
    notes_md = models.TextField("поради автора", max_length=5000, blank=True)
    notes_html = models.TextField(blank=True, editable=False)
    forked_from = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="forks"
    )
    forks_count = models.PositiveIntegerField(default=0)

    # Modrinth modpacks (origin=modrinth)
    external_id = models.CharField("id на Modrinth", max_length=16, blank=True)
    external_url = models.URLField("сторінка на Modrinth", max_length=500, blank=True)
    modrinth_version_id = models.CharField(max_length=16, blank=True)
    icon_url = models.URLField(max_length=500, blank=True)
    source_file_url = models.URLField(max_length=500, blank=True)
    modrinth_downloads = models.PositiveBigIntegerField(default=0)
    synced_at = models.DateTimeField("синхронізовано", null=True, blank=True)

    class Meta:
        verbose_name = "збірка"
        verbose_name_plural = "збірки"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-published_at"], name="packs_pack_status_published"),
            models.Index(fields=["origin", "game_version", "loader"], name="packs_pack_target"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["external_id"],
                condition=~Q(external_id=""),
                name="packs_pack_external_id_unique",
            )
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def is_modrinth(self) -> bool:
        return self.origin == Origin.MODRINTH


class Reason(models.TextChoices):
    REQUESTED = "requested", "Обрав автор"
    DEPENDENCY = "dependency", "Залежність"
    IMPLICIT = "implicit", "Потрібен неявно"


class Env(models.TextChoices):
    """`env` of a file in modrinth.index.json."""

    REQUIRED = "required", "Потрібен"
    OPTIONAL = "optional", "За бажанням"
    UNSUPPORTED = "unsupported", "Не потрібен"


class PackItem(models.Model):
    """A project in a pack and the file picked for the pack's game version and loader.

    `version` is null when nothing fits or Modrinth dropped the file: the project stays and
    the check says why. `reason` and `required_by` come from the compatibility engine.
    """

    pack = models.ForeignKey(Pack, on_delete=models.CASCADE, related_name="items")
    project = models.ForeignKey("mods.Project", on_delete=models.CASCADE, related_name="+")
    version = models.ForeignKey(
        "mods.ProjectVersion", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    reason = models.CharField(
        "чому тут", max_length=12, choices=Reason.choices, default=Reason.REQUESTED
    )
    #: Slugs of the items that need this one (dependency / implicit)
    required_by = ArrayField(models.CharField(max_length=96), default=list, blank=True)
    env_client = models.CharField(max_length=12, choices=Env.choices, default=Env.REQUIRED)
    env_server = models.CharField(max_length=12, choices=Env.choices, default=Env.REQUIRED)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "елемент збірки"
        verbose_name_plural = "елементи збірки"
        ordering = ["position", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["pack", "project"], name="packs_item_unique_project")
        ]

    def __str__(self) -> str:
        return f"{self.pack_id}: {self.project_id}"


class PackExternalFile(models.Model):
    """A file of a Modrinth modpack that is not a Modrinth project (configs, CurseForge jars).

    We neither pick nor check it: the pack page lists it, the original .mrpack carries it.
    """

    pack = models.ForeignKey(Pack, on_delete=models.CASCADE, related_name="external_files")
    path = models.CharField(max_length=300)
    url = models.URLField(max_length=700, blank=True)
    sha1 = models.CharField(max_length=40, blank=True)
    sha512 = models.CharField(max_length=128, blank=True)
    size = models.PositiveBigIntegerField(default=0)

    class Meta:
        verbose_name = "сторонній файл"
        verbose_name_plural = "сторонні файли"
        ordering = ["path"]
        constraints = [
            models.UniqueConstraint(fields=["pack", "path"], name="packs_external_file_unique")
        ]

    def __str__(self) -> str:
        return self.path


class LoaderRelease(models.Model):
    """The latest stable loader build for a game version (refreshed daily from loader sites)."""

    loader = models.CharField(max_length=16, choices=PackLoader.choices)
    game_version = models.CharField(max_length=32)
    version = models.CharField(max_length=64)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "версія лоадера"
        verbose_name_plural = "версії лоадерів"
        constraints = [
            models.UniqueConstraint(
                fields=["loader", "game_version"], name="packs_loader_release_unique"
            )
        ]

    def __str__(self) -> str:
        return f"{self.loader} {self.version} ({self.game_version})"
