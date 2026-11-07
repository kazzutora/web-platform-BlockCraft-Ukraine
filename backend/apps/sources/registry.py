"""Registry of content sources: what /sources shows and what `make sync s=<key>` runs.

Facts about each API (fields, limits, terms) live in docs/sources.md.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from django.utils.module_loading import import_string

from apps.core.models import Source


@dataclass(frozen=True)
class Job:
    key: str
    title: str
    task: str  # dotted path to a callable that opens `sync_run(...)` itself
    accepts_limit: bool = False

    def load(self) -> Callable[..., object]:
        return import_string(self.task)


@dataclass(frozen=True)
class SourceInfo:
    key: str
    name: str
    description: str
    url: str
    terms_url: str = ""
    jobs: tuple[Job, ...] = field(default_factory=tuple)

    def job(self, key: str) -> Job:
        for job in self.jobs:
            if job.key == key:
                return job
        raise KeyError(key)


SOURCES: tuple[SourceInfo, ...] = (
    SourceInfo(
        key=Source.MODRINTH,
        name="Modrinth",
        description=(
            "Відкрита платформа модів, ресурспаків, шейдерів, датапаків, модпаків і серверів "
            "Minecraft. Звідси — каталог, версії файлів і залежності; файли завантажуються "
            "з CDN Modrinth."
        ),
        url="https://modrinth.com",
        terms_url="https://modrinth.com/legal/terms",
        jobs=(
            Job(
                key="game_versions",
                title="Версії Minecraft: які показуємо в «Моїй грі» й для яких беремо файли",
                task="apps.sources.tasks.sync_game_versions",
            ),
            Job(
                key="catalog",
                title="Каталог: популярні проєкти за типами з їхніми версіями",
                task="apps.mods.tasks.sync_popular",
                accepts_limit=True,
            ),
            Job(
                key="versions",
                title="Версії проєктів, які гравці завантажують і додають у збірки",
                task="apps.mods.tasks.sync_versions_for_tracked",
            ),
        ),
    ),
    SourceInfo(
        key=Source.MINESKIN,
        name="MineSkin",
        description="Публічна галерея скінів Minecraft: текстура, модель і назва кожного скіна.",
        url="https://mineskin.org",
    ),
    SourceInfo(
        key=Source.MOJANG,
        name="Mojang",
        description=(
            "Офіційні профілі гравців Minecraft: скін за ніком. Запит — лише коли гравець "
            "шукає нік, без регулярної синхронізації."
        ),
        url="https://www.minecraft.net",
        terms_url="https://www.minecraft.net/usage-guidelines",
    ),
    SourceInfo(
        key="loaders",
        name="Мета лоадерів",
        description=(
            "Версії Fabric, Quilt, Forge і NeoForge для кожної версії гри — потрібні, щоб "
            "файл .mrpack запускався в лаунчері."
        ),
        url="https://fabricmc.net",
        jobs=(
            Job(
                key="releases",
                title="Останні версії лоадерів для підтримуваних версій гри",
                task="apps.packs.tasks.refresh_loader_versions",
            ),
        ),
    ),
)


def get(key: str) -> SourceInfo:
    for source in SOURCES:
        if source.key == key:
            return source
    raise KeyError(key)
