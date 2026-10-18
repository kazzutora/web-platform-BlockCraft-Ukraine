from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models

from apps.core.models import Engagement, Publishable, TimeStamped


class ProjectType(models.TextChoices):
    MOD = "mod", "Мод"
    RESOURCEPACK = "resourcepack", "Ресурспак"
    SHADER = "shader", "Шейдер"


class Category(models.Model):
    """Modrinth category (tag), translated for the catalog filters."""

    slug = models.SlugField(max_length=64)
    name_uk = models.CharField("назва", max_length=64)
    project_type = models.CharField(max_length=16, choices=ProjectType.choices)
    header = models.CharField("група", max_length=32, blank=True)

    class Meta:
        verbose_name = "категорія"
        verbose_name_plural = "категорії"
        ordering = ["project_type", "name_uk"]
        constraints = [
            models.UniqueConstraint(fields=["project_type", "slug"], name="mods_category_unique")
        ]

    def __str__(self) -> str:
        return f"{self.name_uk} ({self.get_project_type_display()})"


class Project(TimeStamped, Publishable, Engagement):
    """A mod, resource pack or shader from Modrinth. Files stay on Modrinth: we keep links."""

    class GpuLoad(models.TextChoices):
        LIGHT = "light", "Легкий"
        MEDIUM = "medium", "Середній"
        HEAVY = "heavy", "Важкий"

    modrinth_id = models.CharField(max_length=16, unique=True)
    slug = models.SlugField(max_length=96, unique=True)
    project_type = models.CharField(max_length=16, choices=ProjectType.choices, db_index=True)
    title = models.CharField("назва", max_length=128)
    summary = models.CharField("короткий опис (Modrinth)", max_length=512, blank=True)
    summary_uk = models.CharField(
        "короткий опис українською",
        max_length=512,
        blank=True,
        help_text="Пишуть модератори й спільнота; показується замість англійського.",
    )
    body_md = models.TextField("опис (markdown)", blank=True)
    body_html = models.TextField("опис (HTML, очищений)", blank=True, editable=False)
    icon_url = models.URLField(max_length=500, blank=True)
    gallery = models.JSONField(default=list, blank=True)
    categories = models.ManyToManyField(Category, blank=True, related_name="projects")
    loaders = ArrayField(models.CharField(max_length=32), default=list, blank=True)
    game_versions = ArrayField(models.CharField(max_length=32), default=list, blank=True)
    license = models.CharField(max_length=128, blank=True)
    source_url = models.URLField(max_length=500, blank=True)
    modrinth_downloads = models.PositiveBigIntegerField(default=0, db_index=True)
    modrinth_updated_at = models.DateTimeField(null=True, blank=True)
    gpu_load = models.CharField(
        "навантаження на GPU", max_length=8, choices=GpuLoad.choices, blank=True
    )
    gpu_load_manual = models.BooleanField(
        default=False, help_text="Встановлено вручну: синхронізація не перезапише."
    )
    claimed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="claimed_projects",
    )
    suggested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="suggested_projects",
    )
    synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "проєкт"
        verbose_name_plural = "проєкти"
        indexes = [
            GinIndex(fields=["game_versions"], name="mods_project_versions_gin"),
            GinIndex(fields=["loaders"], name="mods_project_loaders_gin"),
            # The default catalog order: published, most downloaded first
            models.Index(fields=["status", "-modrinth_downloads"], name="mods_project_status_dl"),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def modrinth_url(self) -> str:
        return f"https://modrinth.com/{self.project_type}/{self.slug}"


class ProjectVersion(models.Model):
    class VersionType(models.TextChoices):
        RELEASE = "release", "Реліз"
        BETA = "beta", "Бета"
        ALPHA = "alpha", "Альфа"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="versions")
    modrinth_version_id = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=256, blank=True)
    version_number = models.CharField(max_length=128)
    version_type = models.CharField(
        max_length=8, choices=VersionType.choices, default=VersionType.RELEASE
    )
    game_versions = ArrayField(models.CharField(max_length=32), default=list)
    loaders = ArrayField(models.CharField(max_length=32), default=list)
    file_url = models.URLField(max_length=700)
    file_name = models.CharField(max_length=256)
    file_size = models.PositiveBigIntegerField(default=0)
    sha1 = models.CharField(max_length=40, blank=True)
    dependencies = models.JSONField(default=list, blank=True)
    released_at = models.DateTimeField(db_index=True)

    class Meta:
        verbose_name = "версія"
        verbose_name_plural = "версії"
        ordering = ["-released_at"]
        indexes = [
            GinIndex(fields=["game_versions"], name="mods_version_versions_gin"),
            GinIndex(fields=["loaders"], name="mods_version_loaders_gin"),
        ]

    def __str__(self) -> str:
        return f"{self.project} {self.version_number}"
