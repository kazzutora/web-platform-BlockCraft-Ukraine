from celery import shared_task
from django.conf import settings

from apps.accounts.models import User
from apps.core import jobs
from apps.core.exceptions import DomainError
from apps.core.models import Source
from apps.mods.tasks import LONG_TASK
from apps.sources.clients.mineskin import MineSkinClient, MineSkinError, MineSkinNotFoundError
from apps.sources.clients.mojang import MojangClient, MojangError
from apps.sources.runs import sync_run

from . import services
from .importers import NotASkin


@shared_task(name="skins.sync_mineskin", **LONG_TASK)
def sync_mineskin(limit: int | None = None) -> dict[str, int]:
    """Daily: named skins from the MineSkin public gallery, in batches (tech.md 8.3)."""
    per_run = limit or settings.SYNC_SKINS_PER_RUN
    with (
        sync_run(Source.MINESKIN, "mineskin.gallery", {"limit": per_run}) as run,
        MineSkinClient() as client,
        MojangClient() as textures,
    ):
        services.sync_mineskin(client=client, textures=textures, per_run=per_run, run=run)
    return run.as_dict()


@shared_task(
    name="skins.import_skin", autoretry_for=(MineSkinError,), max_retries=2, retry_backoff=5
)
def import_skin(*, job_id: str, kind: str, value: str, user_id: int | None = None) -> int | None:
    """A player adds a skin by nickname (Mojang) or by MineSkin link; the job tells the page."""
    jobs.running(job_id)
    user = User.objects.filter(pk=user_id).first() if user_id else None
    try:
        if kind == "nickname":
            skin, outcome = services.add_by_nickname(nickname=value, user=user)
        else:
            with MineSkinClient() as client, MojangClient() as textures:
                skin, outcome = services.import_mineskin(
                    client=client, textures=textures, uuid=value, added_by=user
                )
    except DomainError as error:
        jobs.failed(job_id, error.code)
        return None
    except MineSkinNotFoundError:
        jobs.failed(job_id, "not_found")
        return None
    except NotASkin as error:
        jobs.failed(job_id, str(error))
        return None
    except MojangError:
        jobs.failed(job_id, "source_unavailable")
        return None
    except MineSkinError:
        if import_skin.request.retries >= import_skin.max_retries:
            jobs.failed(job_id, "source_unavailable")
        raise
    except Exception:
        jobs.failed(job_id, "failed")
        raise
    if skin.is_hidden:
        jobs.failed(job_id, "hidden_skin")
        return None
    jobs.done(job_id, {"id": skin.pk, "title": skin.title, "existing": outcome != "created"})
    return skin.pk
