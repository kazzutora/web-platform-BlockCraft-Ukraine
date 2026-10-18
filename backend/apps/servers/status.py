"""Live status of servers in Redis (`server:status:{id}`, 15 minutes) — what the API shows."""

from collections.abc import Iterable
from dataclasses import asdict

from django.core.cache import cache
from django.utils import timezone

from .clients import PingResult

TTL = 15 * 60


def _key(server_id: int) -> str:
    return f"server:status:{server_id}"


def store(results: dict[int, PingResult]) -> None:
    checked_at = timezone.now().isoformat()
    cache.set_many(
        {_key(pk): {**asdict(result), "checked_at": checked_at} for pk, result in results.items()},
        TTL,
    )


def get_many(server_ids: Iterable[int]) -> dict[int, dict]:
    """{id: status} for servers pinged in the last 15 minutes; missing ones are unknown."""
    keys = {_key(pk): pk for pk in server_ids}
    return {keys[key]: value for key, value in cache.get_many(list(keys)).items()}


def get(server_id: int) -> dict | None:
    return cache.get(_key(server_id))


# Verification checks run in Celery; the page asks for their outcome


def _verify_key(server_id: int) -> str:
    return f"server:verify:{server_id}"


def set_verification(server_id: int, state: str) -> None:
    cache.set(_verify_key(server_id), state, 10 * 60)


def get_verification(server_id: int) -> str | None:
    return cache.get(_verify_key(server_id))
