"""Runs the engine over our catalog and brings in what it is missing (tech.md 9, R3.3)."""

import logging
from collections.abc import Iterable
from dataclasses import dataclass

from django.core.cache import cache
from django.db import transaction

from apps.core.exceptions import DomainError
from apps.core.game import GameContext, Loader
from apps.core.versions import latest_release
from apps.mods.compat_index import CatalogIndex
from apps.mods.models import Project, ProjectType

from . import resolver
from .types import Request, Resolution, Status, Target

logger = logging.getLogger(__name__)

#: The same missing project is queued at most once in this window
IMPORT_LOCK_SECONDS = 10 * 60
#: Modrinth did not have it either: stop promising «довантажуємо» for a day
UNAVAILABLE_SECONDS = 24 * 60 * 60
#: «Що встановити» of one project: the catalog changes only with the nightly syncs
INSTALL_CACHE_SECONDS = 10 * 60
MAIN_LOADERS = (Loader.FABRIC, Loader.NEOFORGE, Loader.FORGE, Loader.QUILT)
#: Shader files built for these engines run on a modded game; Fabric hosts all of them
SHADER_ENGINES = frozenset({"iris", "canvas"})


@dataclass(frozen=True)
class Resolved:
    """A resolution plus what the API needs to show it."""

    resolution: Resolution
    #: Catalog rows of every project the resolution mentions, by Modrinth id
    projects: dict[str, Project]


def target_for(
    project: Project, game: GameContext, *, game_version: str = "", loader: str = ""
) -> Target:
    """The query wins, then «Моя гра», then what the project itself supports best.

    Without a loader a mod takes its main one and an Iris / Canvas shader takes Fabric: a
    guest who chose nothing still gets a file and its engine, not «no version».
    """
    version = game_version or game.game_version or latest_release(project.game_versions)
    chosen = loader or game.loader
    if not chosen:
        if project.project_type == ProjectType.MOD:
            chosen = next(
                (name for name in MAIN_LOADERS if name in project.loaders), Loader.VANILLA
            )
        elif project.project_type == ProjectType.SHADER and SHADER_ENGINES & set(project.loaders):
            chosen = Loader.FABRIC
        else:
            chosen = Loader.VANILLA
    return Target(version, chosen)


def _lock_key(pid: str) -> str:
    return f"compat:import:{pid}"


def _unavailable_key(pid: str) -> str:
    return f"compat:unavailable:{pid}"


def queue_missing(ids: Iterable[str]) -> list[str]:
    """Starts imports of missing projects (ids or slugs), each once per window."""
    from apps.mods import tasks

    queued = [pid for pid in ids if cache.add(_lock_key(pid), 1, IMPORT_LOCK_SECONDS)]

    def start() -> None:
        try:
            tasks.import_missing.delay(queued)
        except Exception:
            # The broker is down: let the next page view try again instead of in 10 minutes
            cache.delete_many([_lock_key(pid) for pid in queued])
            logger.warning("Could not queue the import of %s", queued, exc_info=True)

    if queued:
        transaction.on_commit(start)
    return queued


def mark_unavailable(ids: Iterable[str]) -> None:
    """Called by the import task for what Modrinth did not return."""
    cache.set_many(dict.fromkeys(map(_unavailable_key, ids), 1), UNAVAILABLE_SECONDS)


def _split_unavailable(resolution: Resolution) -> None:
    if not resolution.missing:
        return
    gone = cache.get_many([_unavailable_key(pid) for pid in resolution.missing])
    resolution.unavailable = [pid for pid in resolution.missing if _unavailable_key(pid) in gone]
    resolution.missing = [pid for pid in resolution.missing if pid not in resolution.unavailable]


#: A finished modpack may hold many more files than a player may ask about at once
TRUSTED_LIMIT = 2000


def resolve(
    *, items: list[tuple[Project, str | None]], target: Target, trust_pins: bool = False
) -> Resolved:
    """`items` are catalog projects with an optional pinned version id.

    `trust_pins` — a modpack as shipped (see `resolver.resolve`); no 300-project limit.
    """
    limit = TRUSTED_LIMIT if trust_pins else resolver.MAX_PROJECTS
    if len(items) > limit:
        raise DomainError(
            code="pack_too_large",
            message=f"За раз можна перевірити до {resolver.MAX_PROJECTS} проєктів.",
        )
    index = CatalogIndex()
    engine_projects = index.requests(project for project, _ in items)
    requests = [
        Request(engine, pinned) for engine, (_, pinned) in zip(engine_projects, items, strict=True)
    ]
    resolution = resolver.resolve(requests, target, index, trust_pins=trust_pins, limit=limit)
    _split_unavailable(resolution)
    if resolution.missing:
        queue_missing(resolution.missing)
    suggested = {item.project for item in resolution.suggestions} - set(index.rows)
    projects = dict(index.rows)
    if suggested:
        projects.update(
            {
                row.external_id: row
                for row in Project.objects.visible().filter(external_id__in=suggested)
            }
        )
    return Resolved(resolution, projects)


def install(*, project: Project, target: Target) -> dict:
    """`GET /mods/{slug}/install`, cached: every mod page asks for it on render."""
    from .serializers import resolution_data

    key = f"compat:install:{project.pk}:{target.game_version}:{target.loader}"
    data = cache.get(key)
    if data is None:
        data = resolution_data(resolve(items=[(project, None)], target=target))
        # «Довантажуємо» must turn into the full answer on the next ask, not in 10 minutes
        if data["status"] != Status.INCOMPLETE:
            cache.set(key, data, INSTALL_CACHE_SECONDS)
    return data


def resolve_slugs(*, items: list[tuple[str, str | None]], target: Target) -> Resolved:
    """`POST /compat/resolve`: unknown slugs are a field error, not a silent drop."""
    if len(items) > resolver.MAX_PROJECTS:
        raise DomainError(
            code="pack_too_large",
            message=f"За раз можна перевірити до {resolver.MAX_PROJECTS} проєктів.",
        )
    rows = {
        row.slug: row
        for row in Project.objects.visible().filter(slug__in={slug for slug, _ in items})
    }
    unknown = sorted({slug for slug, _ in items} - set(rows))
    if unknown:
        raise DomainError(
            code="unknown_projects",
            message="Деяких проєктів немає в каталозі.",
            fields={"items": [f"Немає в каталозі: {', '.join(unknown)}."]},
            extra={"unknown": unknown},
        )
    return resolve(items=[(rows[slug], pinned) for slug, pinned in items], target=target)
