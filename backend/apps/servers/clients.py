"""Server List Ping via mcstatus. Call it only from Celery tasks."""

import asyncio
import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from mcstatus import BedrockServer, JavaServer

from . import validators
from .choices import Edition

logger = logging.getLogger(__name__)

TIMEOUT = 3.0
CONCURRENCY = 20


@dataclass(frozen=True)
class PingResult:
    is_online: bool
    players_online: int = 0
    players_max: int = 0
    latency_ms: int | None = None
    version_name: str = ""
    motd: str = ""


OFFLINE = PingResult(is_online=False)


@dataclass(frozen=True)
class Target:
    id: int
    host: str
    port: int
    edition: str


async def _is_public(host: str, port: int) -> bool:
    if await asyncio.to_thread(validators.resolve_public, host, port):
        return True
    logger.warning("Ping of %s:%s skipped: it resolves to a private address", host, port)
    return False


async def _java(host: str, port: int) -> PingResult:
    # The default port lets mcstatus follow SRV records (play.example.com → node3:25577);
    # the lookup only reads DNS, the connection goes to the final host once it is checked
    address = host if port == 25565 else f"{host}:{port}"
    server = await JavaServer.async_lookup(address, timeout=TIMEOUT)
    if not await _is_public(server.address.host, server.address.port):
        return OFFLINE
    status = await server.async_status()
    return PingResult(
        is_online=True,
        players_online=status.players.online,
        players_max=status.players.max,
        latency_ms=round(status.latency),
        version_name=status.version.name[:64],
        motd=status.motd.to_plain(),
    )


async def _bedrock(host: str, port: int) -> PingResult:
    if not await _is_public(host, port):
        return OFFLINE
    status = await BedrockServer(host, port, timeout=TIMEOUT).async_status()
    return PingResult(
        is_online=True,
        players_online=status.players.online,
        players_max=status.players.max,
        latency_ms=round(status.latency),
        version_name=status.version.name[:64],
        motd=status.motd.to_plain(),
    )


async def ping(target: Target) -> PingResult:
    """Online status of one server; any network error or timeout means offline."""
    probe = _bedrock if target.edition == Edition.BEDROCK else _java
    try:
        return await asyncio.wait_for(probe(target.host, target.port), TIMEOUT + 1)
    # mcstatus raises many kinds of network errors: all of them mean «offline»
    except Exception as error:
        logger.debug("Ping of %s:%s failed: %r", target.host, target.port, error)
        return OFFLINE


async def ping_many(
    targets: Iterable[Target], *, probe: Callable = ping, concurrency: int = CONCURRENCY
) -> dict[int, PingResult]:
    semaphore = asyncio.Semaphore(concurrency)

    async def one(target: Target) -> tuple[int, PingResult]:
        async with semaphore:
            return target.id, await probe(target)

    return dict(await asyncio.gather(*(one(target) for target in targets)))
