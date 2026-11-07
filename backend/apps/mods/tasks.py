import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.core.exceptions import DomainError
from apps.core.models import Source
from apps.sources.clients.modrinth import ModrinthClient, ModrinthError, ModrinthNotFoundError
from apps.sources.runs import sync_run
from apps.sources.services import supported_game_versions

from . import services
from .models import Project, ProjectType

logger = logging.getLogger(__name__)

# A full sync makes ~600 requests; Modrinth allows 300 per minute
LONG_TASK = {"time_limit": 60 * 60, "soft_time_limit": 55 * 60}


@shared_task(name="mods.sync_popular", **LONG_TASK)
def sync_popular(limit: int | None = None) -> dict[str, dict[str, int]]:
    """One `SyncRun` per project type (`modrinth.catalog:<type>`); `limit` overrides settings."""
    limits = {
        project_type: limit or settings.SYNC_LIMITS[project_type]
        for project_type in ProjectType.values
    }
    counts: dict[str, dict[str, int]] = {}
    with ModrinthClient() as client:
        for project_type, type_limit in limits.items():
            with sync_run(
                Source.MODRINTH, f"modrinth.catalog:{project_type}", {"limit": type_limit}
            ) as run:
                services.sync_popular(
                    client=client,
                    limits={project_type: type_limit},
                    game_versions=supported_game_versions(),
                    run=run,
                )
            counts[project_type] = run.as_dict()
    return counts


@shared_task(name="mods.sync_versions_for_tracked", **LONG_TASK)
def sync_versions_for_tracked(days: int = 90) -> dict[str, int]:
    """Refreshes versions of recently downloaded projects and of those in packs.

    Projects outside the popular sync (pack dependencies, modpack contents) stay fresh this
    way; stage 16 adds favorites.
    """
    from apps.packs.models import PackItem

    since = timezone.now() - timedelta(days=days)
    project_ids = (
        Project.objects.published()
        .filter(
            Q(user_downloads__created_at__gte=since)
            | Q(pk__in=PackItem.objects.values("project_id"))
        )
        .values_list("pk", flat=True)
        .distinct()
    )
    with (
        sync_run(Source.MODRINTH, "modrinth.versions", {"days": days}) as run,
        ModrinthClient() as client,
    ):
        for project in Project.objects.filter(pk__in=list(project_ids)).iterator(chunk_size=100):
            with run.item(project=project.slug):
                services.sync_project_versions(
                    client=client,
                    project=project,
                    game_versions=supported_game_versions(),
                )
                run.updated += 1
    return run.as_dict()


@shared_task(
    name="mods.import_project", autoretry_for=(ModrinthError,), max_retries=3, retry_backoff=60
)
def import_project(*, slug: str, suggested_by_id: int | None = None) -> str | None:
    """Imports a suggested project; unknown slugs are dropped (stage 8 notifies the player)."""
    suggested_by = User.objects.filter(pk=suggested_by_id).first() if suggested_by_id else None
    with ModrinthClient() as client:
        try:
            project = services.import_suggested(
                client=client,
                slug=slug,
                suggested_by=suggested_by,
                game_versions=supported_game_versions(),
            )
        except DomainError:
            logger.info("Suggested project %s is not a mod, pack or shader", slug)
            return None
        except ModrinthNotFoundError:
            logger.info("Suggested project %s does not exist on Modrinth", slug)
            return None
    return project.slug
