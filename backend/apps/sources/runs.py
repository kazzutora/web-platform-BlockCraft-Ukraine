"""Journal of synchronizations: every job that reads a source runs inside `sync_run(...)`."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from django.utils import timezone

from .models import SyncRun

logger = logging.getLogger(__name__)

MAX_ERRORS = 20
#: Longer than any task's hard time limit: a run still «running» after this was killed
STALE_AFTER = timedelta(hours=2)
INTERRUPTED = "Interrupted: the worker stopped before the run finished."


@dataclass
class SyncCounter:
    """Counts what a job did with each item; jobs increment the fields directly."""

    created: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)

    def fail(self, error: BaseException | str, **context: Any) -> None:
        """One item could not be processed; the job goes on."""
        self.failed += 1
        self.note(error, **context)

    def note(self, error: BaseException | str, **context: Any) -> None:
        """Keeps the error as an example without counting an item."""
        if len(self.errors) >= MAX_ERRORS:
            return
        entry: dict[str, Any] = {"message": str(error)[:500]}
        if isinstance(error, BaseException):
            entry["type"] = type(error).__name__
        if context:
            entry["context"] = {key: str(value)[:200] for key, value in context.items()}
        self.errors.append(entry)

    @contextmanager
    def item(self, **context: Any) -> Iterator[None]:
        """Processes one item: an exception counts as failed instead of stopping the job."""
        try:
            yield
        except Exception as error:
            logger.warning("Sync item failed: %s", context, exc_info=True)
            self.fail(error, **context)

    @property
    def processed(self) -> int:
        return self.created + self.updated + self.unchanged

    def status(self) -> str:
        if not self.failed:
            return SyncRun.Status.OK
        return SyncRun.Status.PARTIAL if self.processed or self.skipped else SyncRun.Status.FAILED

    def as_dict(self) -> dict[str, int]:
        return {
            "created": self.created,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "skipped": self.skipped,
            "failed": self.failed,
        }


@contextmanager
def sync_run(source: str, job: str, params: dict[str, Any] | None = None) -> Iterator[SyncCounter]:
    """Records a `SyncRun`: running on enter, counters and status on exit.

    An exception that escapes the block marks the run as failed and is re-raised, so Celery
    still sees the task fail.
    """
    _check_registered(source, job)
    _close_stale(source, job)
    run = SyncRun.objects.create(source=source, job=job, params=params or {})
    counter = SyncCounter()
    try:
        yield counter
    except BaseException as error:
        counter.note(error, stage="run")
        _finish(run, counter, SyncRun.Status.FAILED)
        raise
    _finish(run, counter, counter.status())


def _check_registered(source: str, job: str) -> None:
    """`modrinth.catalog:mod` must belong to a registry job, or /sources would never show it."""
    from . import registry

    name = job.split(":", 1)[0]
    try:
        info = registry.get(source)
    except KeyError as error:
        raise ValueError(f"Unknown source {source!r}") from error
    if not any(name == f"{source}.{item.key}" for item in info.jobs):
        raise ValueError(f"{job!r} is not a job of {source!r} in sources.registry")


def _close_stale(source: str, job: str) -> None:
    """A killed worker (time limit, OOM, deploy) leaves its run «running» forever: close it."""
    now = timezone.now()
    SyncRun.objects.filter(
        source=source,
        job=job,
        status=SyncRun.Status.RUNNING,
        started_at__lt=now - STALE_AFTER,
    ).update(status=SyncRun.Status.FAILED, finished_at=now, errors=[{"message": INTERRUPTED}])


def _finish(run: SyncRun, counter: SyncCounter, status: str) -> None:
    for name, value in counter.as_dict().items():
        setattr(run, name, value)
    run.errors = counter.errors
    run.status = status
    run.finished_at = timezone.now()
    run.save()
    # /sources shows the new run right away instead of after its cache expires; a cache
    # outage must not replace the job's own result or error
    from .selectors import forget_sources

    try:
        forget_sources()
    except Exception:
        logger.warning("Could not reset the /sources cache", exc_info=True)
