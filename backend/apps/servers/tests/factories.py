import factory
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.core.models import Source
from apps.servers.models import ContentKind, Server, ServerSnapshot
from apps.sources.clients.ping import PingResult


class ServerFactory(factory.django.DjangoModelFactory):
    """A server mirrored from Modrinth, as the catalog is made of; `owned()` for one added here."""

    class Meta:
        model = Server

    source = Source.MODRINTH
    external_id = factory.Sequence(lambda n: f"SRV{n:05d}")
    external_url = factory.LazyAttribute(lambda s: f"https://modrinth.com/server/{s.slug}")
    name = factory.Sequence(lambda n: f"Сервер {n}")
    slug = factory.Sequence(lambda n: f"server-{n}")
    java_host = factory.Sequence(lambda n: f"play{n}.example.com")
    java_port = 25565
    languages = factory.LazyFunction(lambda: ["uk"])
    categories = factory.LazyFunction(lambda: ["smp"])
    content_kind = ContentKind.VANILLA
    supported_versions = factory.LazyFunction(lambda: ["1.21.1"])
    recommended_version = "1.21.1"
    synced_at = factory.LazyFunction(timezone.now)

    class Params:
        owned = factory.Trait(
            source=Source.OWNER,
            external_id=factory.LazyAttribute(lambda s: f"{s.java_host}:{s.java_port}"),
            external_url="",
            owner=factory.SubFactory(UserFactory),
            is_verified=True,
        )


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
