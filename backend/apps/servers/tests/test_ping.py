import asyncio
from types import SimpleNamespace

import pytest
from django.core.cache import cache

from apps.servers import clients, services, status, validators
from apps.servers.models import Server, ServerSnapshot
from apps.servers.tasks import ping_all

from .factories import ServerFactory, fake_probe, online

pytestmark = pytest.mark.django_db


def java_status(players=7, motd="Козацький сервер bc-abc123"):
    return SimpleNamespace(
        players=SimpleNamespace(online=players, max=50),
        version=SimpleNamespace(name="Paper 1.21.4"),
        latency=42.6,
        motd=SimpleNamespace(to_plain=lambda: motd),
    )


class FakeJava:
    """Stands in for mcstatus.JavaServer: `lookup` may follow an SRV record elsewhere."""

    def __init__(self, host, port, *, answer=None, error=None):
        self.address = SimpleNamespace(host=host, port=port)
        self._answer, self._error = answer, error

    async def async_status(self):
        if self._error:
            raise self._error
        return self._answer


@pytest.fixture
def public_dns(monkeypatch):
    monkeypatch.setattr(validators, "resolve_public", lambda host, port: [host])


def use_java(monkeypatch, *, srv_host=None, **kwargs):
    async def lookup(address, timeout=3):
        host, _, port = address.partition(":")
        return FakeJava(srv_host or host, int(port or 25565), **kwargs)

    monkeypatch.setattr(clients.JavaServer, "async_lookup", staticmethod(lookup))


def target(host="mc.example.com", port=25565, edition="java"):
    return clients.Target(id=1, host=host, port=port, edition=edition)


def test_online_java_server(monkeypatch, public_dns):
    use_java(monkeypatch, answer=java_status())

    result = asyncio.run(clients.ping(target()))

    assert result == clients.PingResult(
        is_online=True,
        players_online=7,
        players_max=50,
        latency_ms=43,
        version_name="Paper 1.21.4",
        motd="Козацький сервер bc-abc123",
    )


def test_timeouts_and_errors_mean_offline(monkeypatch, public_dns):
    use_java(monkeypatch, error=TimeoutError())
    assert asyncio.run(clients.ping(target())) == clients.OFFLINE

    use_java(monkeypatch, error=ConnectionRefusedError())
    assert asyncio.run(clients.ping(target())) == clients.OFFLINE


def test_srv_record_into_a_private_network_is_not_pinged(monkeypatch):
    use_java(monkeypatch, srv_host="10.0.0.7", answer=java_status())
    monkeypatch.setattr(
        validators, "resolve_public", lambda host, port: [] if host.startswith("10.") else [host]
    )

    assert asyncio.run(clients.ping(target())) == clients.OFFLINE


def test_bedrock_servers_use_the_bedrock_protocol(monkeypatch, public_dns):
    class FakeBedrock:
        def __init__(self, host, port, timeout=3):
            self.port = port

        async def async_status(self):
            return java_status(players=3, motd="Bedrock UA")

    monkeypatch.setattr(clients, "BedrockServer", FakeBedrock)

    result = asyncio.run(clients.ping(target(port=19132, edition="bedrock")))

    assert (result.is_online, result.players_online) == (True, 3)


def test_ping_many_limits_concurrency():
    running, peak = 0, 0

    async def probe(item):
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.01)
        running -= 1
        return online()

    targets = [
        clients.Target(id=n, host=f"h{n}.example.com", port=25565, edition="java")
        for n in range(12)
    ]
    results = asyncio.run(clients.ping_many(targets, probe=probe, concurrency=3))

    assert len(results) == 12
    assert peak == 3


def test_ping_all_stores_status_snapshots_and_last_online():
    up = ServerFactory(host="up.example.com")
    down = ServerFactory(host="down.example.com")
    ServerFactory(host="hidden.example.com", status=Server.Status.HIDDEN)

    count = services.ping_all(probe=fake_probe({"up.example.com": online(players=25)}))

    assert count == 1
    assert status.get(up.pk)["players_online"] == 25
    assert status.get(down.pk)["is_online"] is False
    assert ServerSnapshot.objects.count() == 2
    up.refresh_from_db()
    down.refresh_from_db()
    assert up.last_online_at is not None
    assert down.last_online_at is None


def test_ping_all_works_in_batches():
    ServerFactory.create_batch(5)

    services.ping_all(batch_size=2, probe=fake_probe({}))

    assert ServerSnapshot.objects.count() == 5


def test_ping_all_task_is_scheduled_every_five_minutes(settings, monkeypatch):
    entry = settings.CELERY_BEAT_SCHEDULE["servers-ping-all"]
    assert entry["task"] == "servers.ping_all"
    assert entry["schedule"].minute == set(range(0, 60, 5))

    monkeypatch.setattr(services.clients, "ping", fake_probe({}))
    ServerFactory()
    cache.clear()
    assert ping_all.delay().get() == 0


def test_formatting_codes_are_dropped_from_the_version(monkeypatch, public_dns):
    answer = java_status()
    answer.version.name = "§f§f§fWe support: §l1.20-1.21"
    use_java(monkeypatch, answer=answer)

    assert asyncio.run(clients.ping(target())).version_name == "We support: 1.20-1.21"
