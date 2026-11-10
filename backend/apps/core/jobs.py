"""Background jobs a player waits for (`POST /mods/import` → `GET /jobs/{id}`).

State lives in Redis for a day: a job is a short-lived receipt, not a record worth a table.
The id is a random UUID, so whoever holds it may read the state.
"""

import uuid
from typing import Any, TypedDict

from django.core.cache import cache

TTL = 24 * 60 * 60


class State:
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

    values = (QUEUED, RUNNING, DONE, FAILED)


class Job(TypedDict):
    id: str
    kind: str
    status: str
    #: What the job produced, e.g. {"slug": "sodium"}
    result: dict[str, Any] | None
    #: Why it failed: an error code the frontend explains, e.g. "not_found"
    error: str


def _key(job_id: str) -> str:
    return f"job:{job_id}"


def create(kind: str) -> Job:
    job: Job = {
        "id": str(uuid.uuid4()),
        "kind": kind,
        "status": State.QUEUED,
        "result": None,
        "error": "",
    }
    cache.set(_key(job["id"]), job, TTL)
    return job


def get(job_id: str) -> Job | None:
    try:
        uuid.UUID(job_id)
    except ValueError:
        return None
    return cache.get(_key(job_id))


def update(job_id: str, **changes: Any) -> None:
    job = get(job_id)
    if job is None:
        return
    cache.set(_key(job_id), {**job, **changes}, TTL)


def running(job_id: str) -> None:
    update(job_id, status=State.RUNNING)


def done(job_id: str, result: dict[str, Any]) -> None:
    update(job_id, status=State.DONE, result=result)


def failed(job_id: str, error: str) -> None:
    update(job_id, status=State.FAILED, error=error)
