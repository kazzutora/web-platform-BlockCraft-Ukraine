from typing import Any

from django.core.cache import cache

from apps.core.game import Loader

from . import registry
from .models import GameVersion, SyncRun

META_KEY = "sources:meta"
META_TTL = 10 * 60


def meta() -> dict[str, Any]:
    """What every form and filter needs: supported versions, loaders, categories (GET /meta)."""
    return cache.get_or_set(META_KEY, _build_meta, META_TTL)


def _build_meta() -> dict[str, Any]:
    from apps.mods.models import Category

    return {
        "game_versions": list(GameVersion.objects.supported()),
        "loaders": list(Loader.values),
        "categories": list(Category.objects.all()),
    }


def forget_meta() -> None:
    cache.delete(META_KEY)


SOURCES_KEY = "sources:overview"
SOURCES_TTL = 60
# The worst status wins when one job writes several runs (the catalog: one per type)
_SEVERITY = {
    SyncRun.Status.OK: 0,
    SyncRun.Status.RUNNING: 1,
    SyncRun.Status.PARTIAL: 2,
    SyncRun.Status.FAILED: 3,
}
_COUNTERS = ("created", "updated", "unchanged", "skipped", "failed")


def sources_overview() -> list[dict[str, Any]]:
    """Every registered source with the latest run of each job (GET /sources)."""
    return cache.get_or_set(SOURCES_KEY, _build_sources, SOURCES_TTL)


def _build_sources() -> list[dict[str, Any]]:
    latest = list(
        SyncRun.objects.order_by("source", "job", "-started_at").distinct("source", "job")
    )
    overview = []
    for info in registry.SOURCES:
        jobs = []
        for job in info.jobs:
            name = f"{info.key}.{job.key}"
            runs = [
                run
                for run in latest
                if run.source == info.key and (run.job == name or run.job.startswith(f"{name}:"))
            ]
            jobs.append({"key": job.key, "title": job.title, "last_run": _summary(runs)})
        finished = [job["last_run"] for job in jobs if job["last_run"]]
        overview.append(
            {
                "key": info.key,
                "name": info.name,
                "description": info.description,
                "url": info.url,
                "terms_url": info.terms_url,
                "last_sync": max(finished, key=lambda run: run["started_at"], default=None),
                "jobs": jobs,
            }
        )
    return overview


def _summary(runs: list[SyncRun]) -> dict[str, Any] | None:
    if not runs:
        return None
    finished = [run.finished_at for run in runs if run.finished_at]
    return {
        "status": max((run.status for run in runs), key=_SEVERITY.__getitem__),
        "started_at": min(run.started_at for run in runs),
        "finished_at": max(finished) if len(finished) == len(runs) else None,
        **{name: sum(getattr(run, name) for run in runs) for name in _COUNTERS},
    }


def forget_sources() -> None:
    cache.delete(SOURCES_KEY)
