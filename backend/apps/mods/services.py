"""Catalog syncs and player actions on mods. Mapping of Modrinth data lives in importers."""

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from apps.accounts.models import User
from apps.core import jobs
from apps.core.counters import bump
from apps.core.exceptions import DomainError
from apps.core.models import Source
from apps.library.models import Download
from apps.sources.clients.modrinth import ModrinthClient
from apps.sources.runs import SyncCounter

from . import importers
from .importers import Outcome
from .models import Project, ProjectVersion

logger = logging.getLogger(__name__)

BATCH = 100  # Modrinth's maximum `limit` and a safe size for `/projects?ids=`
#: Projects outside the top-N (added by link, dependencies, modpack contents) are refreshed
#: by the versions job once their metadata is older than this
STALE_AFTER = timedelta(hours=20)


def _count(run: SyncCounter, outcome: Outcome) -> None:
    setattr(run, outcome.value, getattr(run, outcome.value) + 1)


def top_project_ids(
    *, client: ModrinthClient, project_type: str, limit: int, game_versions: list[str]
) -> list[str]:
    """Ids of the most downloaded projects of a type with files for supported versions."""
    ids: list[str] = []
    offset = 0
    while len(ids) < limit:
        page = client.search(
            project_type=project_type,
            game_versions=game_versions,
            offset=offset,
            limit=min(BATCH, limit - len(ids)),
        )
        ids.extend(hit.project_id for hit in page.hits if hit.project_id not in ids)
        offset += len(page.hits)
        if not page.hits or offset >= page.total_hits:
            break
    return ids[:limit]


def sync_catalog(
    *,
    client: ModrinthClient,
    project_type: str,
    limit: int,
    game_versions: list[str],
    run: SyncCounter,
    progress: Callable[[str], None] = logger.info,
) -> None:
    """Top-N projects of one type: new ones are created, changed pages refreshed.

    Versions are left to `sync_versions`, which reads only projects whose page changed.
    A failing project is counted in `run` and the rest of the batch goes on.
    """
    ids = top_project_ids(
        client=client, project_type=project_type, limit=limit, game_versions=game_versions
    )
    progress(f"{project_type}: {len(ids)} projects found")
    for start in range(0, len(ids), BATCH):
        for data in client.get_projects(ids[start : start + BATCH]):
            with run.item(project=data.slug):
                if importers.project_type_of(data) is None:
                    run.skipped += 1
                    continue
                _, outcome = importers.import_project(data)
                _count(run, outcome)
        progress(f"{project_type}: {min(start + BATCH, len(ids))}/{len(ids)}")


def sync_project_versions(
    *, client: ModrinthClient, project: Project, game_versions: Iterable[str]
) -> int:
    game_versions = list(game_versions)
    versions = client.get_versions(project.external_id, game_versions=game_versions)
    return importers.import_versions(project, versions, game_versions=game_versions)


def refresh_stale(*, client: ModrinthClient, run: SyncCounter) -> None:
    """Metadata of projects the catalog sync did not touch lately, 100 per request."""
    cutoff = timezone.now() - STALE_AFTER
    ids = list(
        Project.objects.filter(source=Source.MODRINTH)
        .filter(Q(synced_at__isnull=True) | Q(synced_at__lt=cutoff))
        .values_list("external_id", flat=True)
    )
    for start in range(0, len(ids), BATCH):
        batch = ids[start : start + BATCH]
        found = client.get_projects(batch)
        # Deleted or made private on Modrinth: kept as is, the moderator decides
        run.skipped += len(batch) - len(found)
        for data in found:
            with run.item(project=data.slug):
                _, outcome = importers.import_project(data)
                _count(run, outcome)


def sync_versions(
    *, client: ModrinthClient, game_versions: list[str], run: SyncCounter, full: bool = False
) -> None:
    """Versions of every project whose Modrinth page changed since we last read them.

    Modrinth bumps a project's `updated` when a version is published, so an unchanged page
    means unchanged versions. `created` counts projects read for the first time,
    `updated` re-read ones, `unchanged` the ones skipped as fresh.
    """
    refresh_stale(client=client, run=run)
    queue = Project.objects.filter(source=Source.MODRINTH)
    if not full:
        queue = queue.filter(
            Q(versions_synced_at__isnull=True) | Q(versions_synced_at__lt=F("modrinth_updated_at"))
        )
    run.unchanged += Project.objects.filter(source=Source.MODRINTH).count() - queue.count()
    for project in queue.order_by("-modrinth_downloads").iterator(chunk_size=BATCH):
        first_time = project.versions_synced_at is None
        with run.item(project=project.slug):
            sync_project_versions(client=client, project=project, game_versions=game_versions)
            if first_time:
                run.created += 1
            else:
                run.updated += 1


def import_missing(
    *, client: ModrinthClient, modrinth_ids: Iterable[str], game_versions: list[str]
) -> int:
    """Brings in projects other content depends on (pack dependencies, modpack contents)."""
    ids = set(modrinth_ids)
    known = set(
        Project.objects.filter(source=Source.MODRINTH, external_id__in=ids).values_list(
            "external_id", flat=True
        )
    )
    missing = sorted(ids - known)
    imported = 0
    for start in range(0, len(missing), BATCH):
        for data in client.get_projects(missing[start : start + BATCH]):
            if importers.project_type_of(data) is None:
                continue
            project, _ = importers.import_project(data)
            sync_project_versions(client=client, project=project, game_versions=game_versions)
            imported += 1
    return imported


HIDDEN_MESSAGE = "Модератор прибрав цей проєкт із каталогу."


@dataclass(frozen=True)
class ImportRequest:
    """What `POST /mods/import` answers: a job to poll, or the project we already have."""

    job_id: str | None = None
    slug: str = ""
    title: str = ""


def request_import(*, slug: str, user: User) -> ImportRequest:
    """Starts a background import, unless the project is already here (or hidden here)."""
    from . import tasks

    known = Project.objects.filter(slug=slug).first()
    if known is not None and known.is_hidden:
        raise DomainError(
            code="hidden_project", message=HIDDEN_MESSAGE, fields={"url": [HIDDEN_MESSAGE]}
        )
    if known is not None:
        return ImportRequest(slug=known.slug, title=known.title)
    job = jobs.create("mods.import")
    transaction.on_commit(
        lambda: tasks.import_project.delay(job_id=job["id"], slug=slug, user_id=user.pk)
    )
    return ImportRequest(job_id=job["id"])


def import_from_modrinth(
    *, client: ModrinthClient, slug: str, user: User | None, game_versions: list[str]
) -> Project:
    """A player added a Modrinth project by link: visible at once, versions included.

    Modpacks are refused with `is_modpack`: they become packs through /import (R4).
    """
    data = client.get_project(slug)
    if data.project_type == "modpack":
        raise DomainError(code="is_modpack", message="Це збірка, а не мод.")
    hidden = Project.objects.filter(source=Source.MODRINTH, external_id=data.id, is_hidden=True)
    if hidden.exists():
        raise DomainError(code="hidden_project", message=HIDDEN_MESSAGE)
    project, _ = importers.import_project(data, imported_by=user)
    sync_project_versions(client=client, project=project, game_versions=game_versions)
    return project


@transaction.atomic
def record_download(
    *,
    project: Project,
    version: ProjectVersion,
    user: User | None,
    game_version: str = "",
    loader: str = "",
) -> None:
    bump(project, "downloads_count")
    if user is not None and user.is_authenticated:
        Download.objects.create(
            user=user,
            project=project,
            version=version,
            game_version=game_version[:32],
            loader=loader[:32],
        )
