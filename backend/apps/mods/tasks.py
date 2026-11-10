import logging

from celery import shared_task
from django.conf import settings
from django.db.models import Q

from apps.accounts.models import User
from apps.core import jobs
from apps.core.exceptions import DomainError
from apps.core.models import Source
from apps.sources.clients.modrinth import ModrinthClient, ModrinthError, ModrinthNotFoundError
from apps.sources.runs import sync_run
from apps.sources.services import supported_game_versions

from . import importers, services
from .models import Project, ProjectType

logger = logging.getLogger(__name__)

# The first full sync makes ~2000 requests; Modrinth allows 300 per minute
LONG_TASK = {"time_limit": 60 * 60, "soft_time_limit": 55 * 60}


@shared_task(name="mods.sync_catalog", **LONG_TASK)
def sync_catalog(limit: int | None = None) -> dict[str, dict[str, int]]:
    """One `SyncRun` per project type (`modrinth.catalog:<type>`); `limit` overrides settings."""
    game_versions = supported_game_versions()
    counts: dict[str, dict[str, int]] = {}
    categories = None
    with ModrinthClient() as client:
        for project_type in ProjectType.values:
            type_limit = limit or settings.SYNC_LIMITS[project_type]
            with sync_run(
                Source.MODRINTH, f"modrinth.catalog:{project_type}", {"limit": type_limit}
            ) as run:
                if categories is None:
                    categories = client.get_categories()
                importers.upsert_categories(categories, project_type=project_type)
                services.sync_catalog(
                    client=client,
                    project_type=project_type,
                    limit=type_limit,
                    game_versions=game_versions,
                    run=run,
                )
            counts[project_type] = run.as_dict()
    return counts


@shared_task(name="mods.sync_versions", **LONG_TASK)
def sync_versions(full: bool = False) -> dict[str, int]:
    """Versions of projects whose Modrinth page changed; `full` re-reads every project."""
    with (
        sync_run(Source.MODRINTH, "modrinth.versions", {"full": full}) as run,
        ModrinthClient() as client,
    ):
        services.sync_versions(
            client=client, game_versions=supported_game_versions(), run=run, full=full
        )
    return run.as_dict()


@shared_task(
    name="mods.import_project", autoretry_for=(ModrinthError,), max_retries=2, retry_backoff=5
)
def import_project(*, job_id: str, slug: str, user_id: int | None = None) -> str | None:
    """A player added a Modrinth project by link; the job tells the page how it went."""
    jobs.running(job_id)
    user = User.objects.filter(pk=user_id).first() if user_id else None
    try:
        with ModrinthClient() as client:
            project = services.import_from_modrinth(
                client=client, slug=slug, user=user, game_versions=supported_game_versions()
            )
    except ModrinthNotFoundError:
        jobs.failed(job_id, "not_found")
        return None
    except DomainError as error:
        jobs.failed(job_id, error.code)
        return None
    except ModrinthError:
        if import_project.request.retries >= import_project.max_retries:
            jobs.failed(job_id, "source_unavailable")
        raise
    except Exception:
        # Anything else (a slug clash after a rename) must not leave the page waiting
        jobs.failed(job_id, "failed")
        raise
    jobs.done(
        job_id,
        {
            "slug": project.slug,
            "title": project.title,
            "project_type": str(project.project_type),
        },
    )
    return project.slug


@shared_task(
    name="mods.import_missing", autoretry_for=(ModrinthError,), max_retries=2, retry_backoff=10
)
def import_missing(ids: list[str]) -> int:
    """Dependencies the compatibility engine did not find (ids, or slugs of shader engines).

    What Modrinth does not return either is marked unavailable, so pages stop waiting.
    """
    from apps.compat.services import mark_unavailable

    with ModrinthClient() as client:
        imported = services.import_missing(
            client=client, modrinth_ids=ids, game_versions=supported_game_versions()
        )
    found = Project.objects.filter(Q(external_id__in=ids) | Q(slug__in=ids))
    known = {value for row in found.values_list("external_id", "slug") for value in row}
    mark_unavailable(set(ids) - known)
    return imported


@shared_task(
    name="mods.read_versions", autoretry_for=(ModrinthError,), max_retries=2, retry_backoff=10
)
def read_versions(external_ids: list[str]) -> int:
    """All supported versions of projects that came in with one file (/import)."""
    projects = Project.objects.filter(external_id__in=external_ids, versions_synced_at__isnull=True)
    with ModrinthClient() as client:
        game_versions = supported_game_versions()
        for project in projects:
            services.sync_project_versions(
                client=client, project=project, game_versions=game_versions
            )
    return len(projects)
