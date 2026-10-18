import socket

import pytest

from apps.servers import validators


@pytest.mark.parametrize(
    ("value", "host"),
    [
        ("Play.Example.com", "play.example.com"),
        ("mc.example.com.", "mc.example.com"),
        ("https://mc.example.com/", "mc.example.com"),
        ("8.8.8.8", "8.8.8.8"),
        ("[2001:4860:4860::8888]", "2001:4860:4860::8888"),
    ],
)
def test_public_hosts_are_accepted(value, host):
    assert validators.clean_host(value) == host


@pytest.mark.parametrize(
    "value",
    [
        "localhost",
        "mc.localhost",
        "minecraft.local",
        "db.internal",
        "127.0.0.1",
        "10.0.0.5",
        "192.168.1.20",
        "172.16.0.1",
        "169.254.169.254",  # cloud metadata
        "100.64.0.1",  # carrier-grade NAT
        "0.0.0.0",
        "::1",
        "fd00::1",
        "::ffff:127.0.0.1",
        "224.0.0.1",
        "backend",  # Docker service names are single labels
        "not a host",
        "",
    ],
)
def test_internal_or_broken_hosts_are_rejected(value):
    with pytest.raises(validators.AddressError):
        validators.clean_host(value)


@pytest.mark.parametrize(
    ("value", "split"),
    [
        ("play.example.com:25566", ("play.example.com", 25566)),
        ("play.example.com", ("play.example.com", None)),
        ("[2001:db8::1]:19132", ("2001:db8::1", 19132)),
    ],
)
def test_addresses_split_into_host_and_port(value, split):
    assert validators.split_address(value) == split


@pytest.mark.parametrize("port", [0, 65536])
def test_ports_out_of_range(port):
    with pytest.raises(validators.AddressError):
        validators.clean_port(port)


def fake_dns(monkeypatch, *addresses):
    def getaddrinfo(host, port, **kwargs):
        if not addresses:
            raise socket.gaierror("no such host")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (a, port)) for a in addresses]

    monkeypatch.setattr(validators.socket, "getaddrinfo", getaddrinfo)


def test_resolve_public_accepts_only_public_answers(monkeypatch):
    fake_dns(monkeypatch, "8.8.8.8", "1.1.1.1")
    assert validators.resolve_public("mc.example.com", 25565) == ["1.1.1.1", "8.8.8.8"]

    # DNS that points a public-looking name inside our network
    fake_dns(monkeypatch, "8.8.8.8", "10.0.0.3")
    assert validators.resolve_public("evil.example.com", 25565) == []

    fake_dns(monkeypatch)
    assert validators.resolve_public("gone.example.com", 25565) == []
