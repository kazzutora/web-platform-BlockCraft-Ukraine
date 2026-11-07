import secrets

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models import Q

from apps.core.models import Authored, Engagement, Publishable, TimeStamped

from .choices import PackLoader, Style


def cover_upload_to(instance: "Pack", filename: str) -> str:
    return f"packs/covers/{secrets.token_hex(8)}.webp"


class Pack(TimeStamped, Authored, Publishable, Engagement):
    """A modpack: mods (and resource packs, shaders) for one game version and loader.

    Files stay on Modrinth: the pack keeps references to versions, `.mrpack` links to them.
    """

    title = models.CharField("назва", max_length=80)
    slug = models.SlugField(max_length=96, unique=True)
    cover = models.ImageField("обкладинка", upload_to=cover_upload_to, blank=True)
    summary = models.CharField("коротко", max_length=280, blank=True)
    style_tags = ArrayField(
        models.CharField(max_length=16, choices=Style.choices), default=list, blank=True
    )
    # A supported sources.GameVersion; packs keep the string to survive version cleanups
    game_version = models.CharField("версія гри", max_length=32)
    loader = models.CharField("лоадер", max_length=16, choices=PackLoader.choices)
    #: Pinned by the author; empty — the latest stable one we know (see LoaderRelease)
    loader_version = models.CharField("версія лоадера", max_length=64, blank=True)
    ram_min_gb = models.PositiveSmallIntegerField("мінімум RAM, ГБ", default=4)
    gpu_note = models.CharField("відеокарта", max_length=140, blank=True)
    install_md = models.TextField("як встановити", max_length=5000, blank=True)
    install_html = models.TextField(blank=True, editable=False)
    changelog_md = models.TextField("що нового", max_length=5000, blank=True)
    changelog_html = models.TextField(blank=True, editable=False)
    forked_from = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="forks"
    )
    forks_count = models.PositiveIntegerField(default=0)
    #: Imported from Modrinth (stage 10.4): the original .mrpack is downloaded from there
    is_official = models.BooleanField("офіційна", default=False)
    modrinth_id = models.CharField(max_length=16, blank=True)
    modrinth_version_id = models.CharField(max_length=16, blank=True)
    icon_url = models.URLField(max_length=500, blank=True)
    source_file_url = models.URLField(max_length=500, blank=True)
    modrinth_downloads = models.PositiveBigIntegerField(default=0)

    class Meta:
        verbose_name = "зборка"
        verbose_name_plural = "зборки"
        ordering = ["-created_at"]
        indexes = [
            GinIndex(fields=["style_tags"], name="packs_pack_styles_gin"),
            models.Index(fields=["status", "-published_at"], name="packs_pack_status_published"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["modrinth_id"],
                condition=~Q(modrinth_id=""),
                name="packs_pack_modrinth_id_unique",
            )
        ]

    def __str__(self) -> str:
        return self.title


class PackItem(models.Model):
    """A project in a pack and the file picked for the pack's game version and loader.

    `version` is cleared when Modrinth drops that file: the project stays and the constructor
    asks to pick another one.
    """

    pack = models.ForeignKey(Pack, on_delete=models.CASCADE, related_name="items")
    project = models.ForeignKey("mods.Project", on_delete=models.CASCADE, related_name="+")
    version = models.ForeignKey(
        "mods.ProjectVersion", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    is_required = models.BooleanField("обов'язковий", default=True)
    #: Pulled in as a required dependency of another item, not picked by the author
    added_as_dependency = models.BooleanField("додано як залежність", default=False)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "елемент зборки"
        verbose_name_plural = "елементи зборки"
        ordering = ["position", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["pack", "project"], name="packs_item_unique_project")
        ]

    def __str__(self) -> str:
        return f"{self.pack_id}: {self.project_id}"


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
