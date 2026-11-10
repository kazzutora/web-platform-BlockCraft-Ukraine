import logging

from celery import shared_task
from django.conf import settings

from apps.core.models import Source
from apps.mods.tasks import LONG_TASK
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.sources.clients.loaders import LoaderClient
from apps.sources.clients.modrinth import ModrinthClient
from apps.sources.runs import sync_run
from apps.sources.services import supported_game_versions

from . import services
from .models import CompatStatus, Origin, Pack

logger = logging.getLogger(__name__)

#: Worse means a player who took the pack may now get a game that does not start
_RANK = {CompatStatus.OK: 0, CompatStatus.WARNINGS: 1, CompatStatus.ERRORS: 2}


@shared_task(name="packs.render_cover")
def render_cover(pack_id: int) -> bool:
    pack = Pack.objects.filter(pk=pack_id).first()
    if pack is None:
        return False
    with ModrinthClient() as client:
        return services.render_cover(client=client, pack=pack)


@shared_task(name="packs.refresh_loader_versions")
def refresh_loader_versions() -> dict[str, int]:
    with sync_run("loaders", "loaders.releases") as run, LoaderClient() as client:
        run.updated += services.store_loader_releases(client.latest_many(supported_game_versions()))
    return run.as_dict()


@shared_task(name="packs.import_official", **LONG_TASK)
def import_official(limit: int | None = None) -> dict[str, int]:
    """`packs.sync_official` of tech.md 11: the most downloaded Modrinth modpacks."""
    limit = limit or settings.SYNC_LIMITS["modpack"]
    with (
        sync_run(Source.MODRINTH, "modrinth.modpacks", {"limit": limit}) as run,
        ModrinthClient() as client,
    ):
        services.import_popular_modpacks(client=client, limit=limit, run=run)
    return run.as_dict()


@shared_task(name="packs.recheck", **LONG_TASK)
def recheck() -> dict[str, int]:
    """After the nightly syncs: published packs checked again; the author hears if worse."""
    counts = {"checked": 0, "worse": 0}
    packs = Pack.objects.filter(status=Pack.Status.PUBLISHED).select_related("author")
    for pack in packs.iterator(chunk_size=100):
        try:
            change = services.recheck(pack)
        except Exception:
            logger.warning("Recheck of pack %s failed", pack.pk, exc_info=True)
            continue
        counts["checked"] += 1
        # Never checked before: nothing got worse, it is simply known now
        worse = change.before in _RANK and _RANK.get(change.after, -1) > _RANK[change.before]
        if worse and pack.origin == Origin.COMMUNITY:
            counts["worse"] += 1
            notify(
                user=pack.author,
                type=Notification.Type.PACK_ATTENTION,
                target=pack,
                reason=change.after,
            )
    return counts
