from celery import shared_task
from django.conf import settings
from django.db import IntegrityError

from apps.core.models import Source
from apps.mods.tasks import LONG_TASK
from apps.sources.clients.modrinth import ModrinthClient, ModrinthError
from apps.sources.clients.modrinth_v3 import ModrinthV3Client
from apps.sources.runs import sync_run
from apps.sources.selectors import forget_meta

from . import services
from .models import Server


@shared_task(name="servers.sync_modrinth", **LONG_TASK)
def sync_modrinth(limit: int | None = None) -> dict[str, int]:
    """Every 6 hours: Modrinth server projects (Ukrainian first); packs come in their tasks."""
    limit = limit or settings.SYNC_LIMITS["servers"]
    with (
        sync_run(Source.MODRINTH, "modrinth.servers", {"limit": limit}) as run,
        ModrinthV3Client() as client,
    ):
        packs = services.sync_modrinth(client=client, limit=limit, run=run)
    forget_meta()  # languages and countries of the catalog may have changed
    for server_id in packs:
        import_required_pack.delay(server_id)
    return run.as_dict()


@shared_task(
    name="servers.import_required_pack",
    # Two packs importing the same mods at once may race on a version: the retry finds it
    autoretry_for=(ModrinthError, IntegrityError),
    max_retries=3,
    retry_backoff=60,
    **LONG_TASK,
)
def import_required_pack(server_id: int) -> bool:
    """The modpack to join a modded server with, as a pack players can take."""
    with ModrinthClient() as client:
        return services.import_required_pack(server_id=server_id, client=client)


@shared_task(name="servers.ping_all")
def ping_all() -> int:
    """Every 5 minutes: status of all servers; returns how many are online."""
    return services.ping_all()


@shared_task(name="servers.ping_server")
def ping_server(server_id: int) -> bool:
    results = services.ping_servers(Server.objects.filter(pk=server_id))
    return bool(results.get(server_id) and results[server_id].is_online)


@shared_task(name="servers.verify_server")
def verify_server(server_id: int, user_id: int) -> str:
    """Pings the server and looks for this player's code in its MOTD."""
    return services.verify(server_id=server_id, user_id=user_id)


@shared_task(name="servers.cleanup_snapshots")
def cleanup_snapshots() -> int:
    return services.cleanup_snapshots()
