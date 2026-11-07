import logging

from celery import shared_task
from django.conf import settings

from apps.core.game import GAME_VERSIONS
from apps.mods.clients import ModrinthClient, ModrinthError
from apps.mods.tasks import LONG_TASK
from apps.sources.runs import sync_run

from . import services
from .clients import LoaderClient
from .models import Pack

logger = logging.getLogger(__name__)


@shared_task(
    name="packs.fill_dependencies", autoretry_for=(ModrinthError,), max_retries=3, retry_backoff=30
)
def fill_dependencies(pack_id: int) -> int:
    """A player added a mod whose dependencies we do not have yet: bring them in."""
    pack = Pack.objects.filter(pk=pack_id).first()
    if pack is None:
        return 0
    with ModrinthClient() as client:
        return services.fill_dependencies(client=client, pack=pack)


@shared_task(name="packs.refresh_loader_versions")
def refresh_loader_versions() -> dict[str, int]:
    with sync_run("loaders", "loaders.releases") as run, LoaderClient() as client:
        run.updated += services.store_loader_releases(client.latest_many(GAME_VERSIONS))
    return run.as_dict()


@shared_task(name="packs.import_official", **LONG_TASK)
def import_official(limit: int | None = None) -> list[str]:
    with ModrinthClient() as client:
        return services.import_popular_modpacks(
            client=client, limit=limit or settings.MODRINTH_OFFICIAL_PACKS
        )
