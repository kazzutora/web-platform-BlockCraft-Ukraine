from celery import shared_task

from apps.core.models import Source

from . import selectors, services
from .clients.modrinth import ModrinthClient
from .runs import sync_run


@shared_task(name="sources.sync_game_versions")
def sync_game_versions() -> dict[str, int]:
    with sync_run(Source.MODRINTH, "modrinth.game_versions") as run, ModrinthClient() as client:
        services.sync_game_versions(client=client, run=run)
    selectors.forget_meta()
    return run.as_dict()
