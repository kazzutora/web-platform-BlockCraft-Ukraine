"""What files a player has (tech.md 9.5 identify / updates). Only hashes come in: the files
never leave the player's computer. Modrinth is asked about hashes we do not know, and every
answer is cached in Redis, so a page view never repeats a request."""

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field

from django.core.cache import cache
from django.db import transaction

from apps.compat import operations, rules
from apps.compat.types import Target
from apps.core.models import Source
from apps.sources.clients.modrinth import ModrinthClient, ModrinthError

from . import importers
from .compat_index import version_of
from .models import Project, ProjectVersion

logger = logging.getLogger(__name__)

HASH_CACHE_SECONDS = 24 * 60 * 60
UPDATES_CACHE_SECONDS = 60 * 60
#: More than a big `mods` folder needs; bounds one request
MAX_FILES = 2000
_UNKNOWN = ""


@dataclass
class Identified:
    #: sha1 → our stored version (with its project)
    known: dict[str, ProjectVersion] = field(default_factory=dict)
    unknown: list[str] = field(default_factory=list)
    guess: operations.Guess = field(default_factory=lambda: operations.Guess(None))
    #: Modrinth did not answer: some files may be known there but not here yet
    source_unavailable: bool = False


def _key(sha1: str) -> str:
    return f"compat:sha1:{sha1}"


def _stored(hashes: Iterable[str]) -> dict[str, ProjectVersion]:
    found: dict[str, ProjectVersion] = {}
    for row in ProjectVersion.objects.filter(sha1__in=list(hashes)).select_related("project"):
        found.setdefault(row.sha1, row)
    return found


def _learn(client: ModrinthClient, hashes: list[str]) -> None:
    """Asks Modrinth about hashes and keeps what it knows: projects and those exact files."""
    found = client.versions_by_hashes(hashes)
    project_ids = {version.project_id for version in found.values()}
    have = set(
        Project.objects.filter(source=Source.MODRINTH, external_id__in=project_ids).values_list(
            "external_id", flat=True
        )
    )
    missing = sorted(project_ids - have)
    for start in range(0, len(missing), 100):
        for data in client.get_projects(missing[start : start + 100]):
            if importers.project_type_of(data) is not None:
                importers.import_project(data)
    if missing:
        # Only the identified file is stored now; the rest of the versions come from Celery
        from . import tasks

        transaction.on_commit(lambda: tasks.read_versions.delay(missing))
    projects = {
        row.external_id: row
        for row in Project.objects.filter(source=Source.MODRINTH, external_id__in=project_ids)
    }
    for sha1, version in found.items():
        project = projects.get(version.project_id)
        file = next((f for f in version.files if f.hashes.get("sha1") == sha1), None)
        if project is None or file is None:
            continue
        ProjectVersion.objects.update_or_create(
            modrinth_version_id=version.id,
            defaults={"project": project, **importers.version_values(version, file)},
        )
    cache.set_many(
        {_key(sha1): sha1 if sha1 in found else _UNKNOWN for sha1 in hashes},
        HASH_CACHE_SECONDS,
    )


def identify(hashes: Iterable[str], *, client: ModrinthClient | None = None) -> Identified:
    wanted = list(dict.fromkeys(sha1.lower() for sha1 in hashes))[:MAX_FILES]
    result = Identified(known=_stored(wanted))
    rest = [sha1 for sha1 in wanted if sha1 not in result.known]
    seen = cache.get_many([_key(sha1) for sha1 in rest])
    ask = [sha1 for sha1 in rest if _key(sha1) not in seen]
    if ask:
        try:
            if client is not None:
                _learn(client, ask)
            else:
                with ModrinthClient() as own:
                    _learn(own, ask)
        except ModrinthError:
            logger.warning("Modrinth did not identify %d files", len(ask), exc_info=True)
            result.source_unavailable = True
        result.known.update(_stored(ask))
    result.unknown = [sha1 for sha1 in wanted if sha1 not in result.known]
    result.guess = operations.guess_target(version_of(row) for row in result.known.values())
    return result


@dataclass(frozen=True)
class Update:
    sha1: str
    current: ProjectVersion
    #: The newest file for the target, or None when the project has none (not ported yet)
    latest: ProjectVersion | None

    @property
    def status(self) -> str:
        if self.latest is None:
            return "not_ported"
        if self.latest.modrinth_version_id == self.current.modrinth_version_id:
            return "up_to_date"
        return "update"


def updates(
    known: dict[str, ProjectVersion], target: Target, *, client: ModrinthClient | None = None
) -> tuple[list[Update], bool]:
    """«Що можна оновити до 26.1»: per file, the newest version for the target."""
    loaders = sorted(rules.accepted_loaders(target, "mod"))
    keys = {sha1: f"compat:update:{sha1}:{target.game_version}:{target.loader}" for sha1 in known}
    cached = cache.get_many(keys.values())
    ask = [sha1 for sha1, key in keys.items() if key not in cached]
    unavailable = False
    if ask:
        try:
            if client is not None:
                answer = client.latest_by_hashes(
                    ask, loaders=loaders, game_versions=[target.game_version]
                )
            else:
                with ModrinthClient() as own:
                    answer = own.latest_by_hashes(
                        ask, loaders=loaders, game_versions=[target.game_version]
                    )
            _keep_versions(answer.values())
            for sha1 in ask:
                version = answer.get(sha1)
                cached[keys[sha1]] = version.id if version else _UNKNOWN
            cache.set_many({keys[sha1]: cached[keys[sha1]] for sha1 in ask}, UPDATES_CACHE_SECONDS)
        except ModrinthError:
            logger.warning("Modrinth did not answer about updates", exc_info=True)
            unavailable = True
    latest_ids = {cached.get(key) for key in keys.values()} - {None, _UNKNOWN}
    rows = {
        row.modrinth_version_id: row
        for row in ProjectVersion.objects.filter(modrinth_version_id__in=latest_ids)
    }
    result = [
        Update(sha1, current, rows.get(cached.get(keys[sha1]) or ""))
        for sha1, current in known.items()
        if keys[sha1] in cached
    ]
    return result, unavailable


def _keep_versions(versions: Iterable) -> None:
    """The newest files Modrinth named: stored so the answer can show and pin them."""
    versions = list(versions)
    projects = {
        row.external_id: row
        for row in Project.objects.filter(
            source=Source.MODRINTH, external_id__in={v.project_id for v in versions}
        )
    }
    for version in versions:
        project = projects.get(version.project_id)
        file = version.primary_file
        if project is None or file is None:
            continue
        ProjectVersion.objects.update_or_create(
            modrinth_version_id=version.id,
            defaults={"project": project, **importers.version_values(version, file)},
        )
