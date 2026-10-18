import socket

import pytest

from apps.servers import clients, validators


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Tests never reach DNS or real servers; a test that needs them mocks them itself."""

    def no_dns(*args, **kwargs):
        raise socket.gaierror("DNS is off in tests")

    async def no_lookup(address, timeout=3):
        raise ConnectionError("network is off in tests")

    monkeypatch.setattr(validators.socket, "getaddrinfo", no_dns)
    monkeypatch.setattr(clients.JavaServer, "async_lookup", staticmethod(no_lookup))
