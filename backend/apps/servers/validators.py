"""Server addresses: what players may add, and what the pinger may connect to (SSRF guard)."""

import ipaddress
import re
import socket

_LABEL = r"(?!-)[a-z0-9-]{1,63}(?<!-)"
HOSTNAME = re.compile(rf"^(?=.{{1,253}}$){_LABEL}(\.{_LABEL})+$")
# Names that only make sense inside someone's network
PRIVATE_SUFFIXES = (".localhost", ".local", ".internal", ".lan", ".home", ".corp", ".intranet")


class AddressError(ValueError):
    pass


def _ip(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return None


def is_public_ip(value: str) -> bool:
    ip = _ip(value)
    if ip is None:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def clean_host(value: str) -> str:
    """Lower-case host without scheme or trailing dot; rejects localhost and private IPs."""
    host = value.strip().lower().removeprefix("http://").removeprefix("https://")
    host = host.split("/", 1)[0].rstrip(".")
    if not host:
        raise AddressError("Вкажи адресу сервера.")
    if _ip(host) is not None:
        if not is_public_ip(host):
            raise AddressError("Це внутрішня адреса: гравці до неї не під’єднаються.")
        return host.strip("[]")
    if host == "localhost" or host.endswith(PRIVATE_SUFFIXES):
        raise AddressError("Це внутрішня адреса: гравці до неї не під’єднаються.")
    if not HOSTNAME.match(host):
        raise AddressError("Адреса має виглядати як play.example.com або IP.")
    return host


def split_address(value: str) -> tuple[str, int | None]:
    """«play.example.com:25566» → host and port; IPv6 goes in brackets: «[2001:db8::1]:25565»."""
    value = value.strip()
    if value.startswith("[") and "]" in value:
        host, _, rest = value[1:].partition("]")
        port = rest.removeprefix(":")
        return host, int(port) if port.isdigit() else None
    if value.count(":") == 1:
        host, port = value.split(":")
        if port.isdigit():
            return host, int(port)
    return value, None


def clean_port(port: int) -> int:
    if not 1 <= port <= 65535:
        raise AddressError("Порт — число від 1 до 65535.")
    return port


def resolve_public(host: str, port: int) -> list[str]:
    """IPs the host points to, only if every one of them is public (checked right before a ping)."""
    if _ip(host) is not None:
        return [host] if is_public_ip(host) else []
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError):
        return []
    addresses = sorted({info[4][0] for info in infos})
    return addresses if addresses and all(is_public_ip(a) for a in addresses) else []
