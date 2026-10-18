from datetime import UTC, datetime

import factory
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.servers.clients import PingResult
from apps.servers.models import Server, ServerSnapshot


class ServerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Server

    author = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Сервер {n}")
    slug = factory.Sequence(lambda n: f"server-{n}")
    host = factory.Sequence(lambda n: f"play{n}.example.com")
    port = 25565
    edition = "java"
    modes = factory.LazyFunction(lambda: ["survival"])
    language = "uk"
    status = Server.Status.PUBLISHED
    published_at = factory.LazyFunction(lambda: datetime(2026, 1, 1, tzinfo=UTC))


class SnapshotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServerSnapshot

    server = factory.SubFactory(ServerFactory)
    ts = factory.LazyFunction(timezone.now)
    is_online = True
    players_online = 10
    players_max = 100


def online(players: int = 12, motd: str = "Ласкаво просимо") -> PingResult:
    return PingResult(
        is_online=True,
        players_online=players,
        players_max=100,
        latency_ms=40,
        version_name="Paper 1.21.4",
        motd=motd,
    )


def fake_probe(results: dict[str, PingResult]):
    """A ping that answers by host: unknown hosts are offline."""

    async def probe(target):
        return results.get(target.host, PingResult(is_online=False))

    return probe
