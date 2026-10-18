import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.accounts.models import User
from apps.core.exceptions import DomainError
from apps.core.game import GAME_VERSIONS

from . import services
from .clients import ModrinthClient, ModrinthError, ModrinthNotFoundError
from .models import Project

logger = logging.getLogger(__name__)

# A full sync makes ~600 requests; Modrinth allows 300 per minute
LONG_TASK = {"time_limit": 60 * 60, "soft_time_limit": 55 * 60}


@shared_task(name="mods.sync_popular", **LONG_TASK)
def sync_popular() -> dict:
    with ModrinthClient() as client:
        result = services.sync_popular(
            client=client,
            limits=settings.MODRINTH_SYNC_LIMITS,
            game_versions=list(GAME_VERSIONS),
        )
    return {
        "categories": result.categories,
        "projects": result.projects,
        "versions": result.versions,
    }


@shared_task(name="mods.sync_versions_for_tracked", **LONG_TASK)
def sync_versions_for_tracked(days: int = 90) -> int:
    """Refreshes versions of recently downloaded projects (stage 16 adds favorites, packs)."""
    since = timezone.now() - timedelta(days=days)
    project_ids = (
        Project.objects.published()
        .filter(user_downloads__created_at__gte=since)
        .values_list("pk", flat=True)
        .distinct()
    )
    synced = 0
    with ModrinthClient() as client:
        for project in Project.objects.filter(pk__in=list(project_ids)).iterator(chunk_size=100):
            try:
                services.sync_project_versions(
                    client=client,
                    project=project,
                    game_versions=list(GAME_VERSIONS),
                )
                synced += 1
            except ModrinthError:
                logger.warning("Could not refresh versions of %s", project.slug, exc_info=True)
    return synced


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
                game_versions=list(GAME_VERSIONS),
            )
        except DomainError:
            logger.info("Suggested project %s is not a mod, pack or shader", slug)
            return None
        except ModrinthNotFoundError:
            logger.info("Suggested project %s does not exist on Modrinth", slug)
            return None
    return project.slug
