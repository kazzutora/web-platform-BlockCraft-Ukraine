import asyncio
import secrets
from collections.abc import Callable, Iterable
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError

from apps.accounts.models import User
from apps.core import publishing
from apps.core.counters import bump
from apps.core.exceptions import DomainError
from apps.core.text import slug_from
from apps.moderation import services as moderation
from apps.moderation import words

from . import clients, status, validators
from .choices import DEFAULT_PORTS, MAX_MODES
from .models import Server, ServerSnapshot, new_verify_code

BANNER_SIZE = (1200, 300)
BANNER_MAX_BYTES = 2 * 1024 * 1024
# Changing these points the listing at another machine: verification starts over
ADDRESS_FIELDS = ("host", "port", "edition")


def _field_error(field: str, message: str, code: str = "invalid") -> DomainError:
    return DomainError(code=code, message=message, fields={field: [message]})


def _check_owner(server: Server, user: User) -> None:
    if server.author_id != user.pk and not user.is_moderator:
        raise DomainError(code="forbidden", message="Це не твій сервер.", status=403)


def clean_address(*, host: str, port: int | None, edition: str) -> tuple[str, int]:
    """Host and port from the form; «host:port» in the host field works too."""
    host, inline_port = validators.split_address(host)
    try:
        host = validators.clean_host(host)
        port = validators.clean_port(port or inline_port or DEFAULT_PORTS[edition])
    except validators.AddressError as error:
        raise _field_error("host", str(error), code="invalid_address") from error
    return host, port


def clean_modes(modes: Iterable[str]) -> list[str]:
    unique = list(dict.fromkeys(modes))
    if not unique:
        raise _field_error("modes", "Обери хоча б один режим.")
    if len(unique) > MAX_MODES:
        raise _field_error("modes", f"Обери до {MAX_MODES} режимів.")
    return unique


def unique_slug(name: str, *, exclude_pk: int | None = None) -> str:
    base = slug_from(name) or f"server-{secrets.token_hex(3)}"
    slug, n = base, 2
    taken = Server.objects.exclude(pk=exclude_pk)
    while taken.filter(slug=slug).exists():
        slug = f"{base[:56]}-{n}"
        n += 1
    return slug


def _queue_ping(server: Server) -> None:
    from . import tasks

    transaction.on_commit(lambda: tasks.ping_server.delay(server.pk))


@transaction.atomic
def create_server(*, author: User, data: dict) -> Server:
    moderation.ensure_can_publish(author)
    words.check(name=data["name"], description=data.get("description", ""))
    host, port = clean_address(host=data["host"], port=data.get("port"), edition=data["edition"])
    if Server.objects.filter(host=host, port=port).exists():
        raise _field_error("host", "Цей сервер уже є в каталозі.", code="server_exists")
    status_ = publishing.initial_status(author)
    server = Server.objects.create(
        author=author,
        name=data["name"].strip(),
        slug=unique_slug(data["name"]),
        host=host,
        port=port,
        edition=data["edition"],
        modes=clean_modes(data["modes"]),
        versions_label=data.get("versions_label", "").strip(),
        language=data["language"],
        description=data.get("description", "").strip(),
        discord_url=data.get("discord_url", ""),
        website_url=data.get("website_url", ""),
        has_whitelist=data.get("has_whitelist", False),
        status=status_,
        published_at=timezone.now() if status_ == Server.Status.PUBLISHED else None,
    )
    publishing.published_on_create(server)
    _queue_ping(server)
    return server


@transaction.atomic
def update_server(*, server: Server, user: User, data: dict) -> Server:
    _check_owner(server, user)
    changed = []
    if any(field in data for field in ADDRESS_FIELDS):
        edition = data.get("edition", server.edition)
        host, port = clean_address(
            host=data.get("host", server.host), port=data.get("port", server.port), edition=edition
        )
        if Server.objects.filter(host=host, port=port).exclude(pk=server.pk).exists():
            raise _field_error("host", "Цей сервер уже є в каталозі.", code="server_exists")
        if (host, port, edition) != (server.host, server.port, server.edition):
            server.host, server.port, server.edition = host, port, edition
            server.is_verified = False
            server.verify_code = new_verify_code()
            changed += [*ADDRESS_FIELDS, "is_verified", "verify_code"]
            _queue_ping(server)
    if "modes" in data:
        server.modes = clean_modes(data["modes"])
        changed.append("modes")
    words.check(name=data.get("name", ""), description=data.get("description", ""))
    for field in ("versions_label", "description", "name"):
        if field in data:
            setattr(server, field, data[field].strip())
            changed.append(field)
    for field in ("language", "discord_url", "website_url", "has_whitelist"):
        if field in data:
            setattr(server, field, data[field])
            changed.append(field)
    if changed:
        server.save(update_fields=[*changed, "updated_at"])
    return server


@transaction.atomic
def delete_server(*, server: Server, user: User) -> None:
    _check_owner(server, user)
    publishing.withdrawn(server)
    banner = server.banner.name if server.banner else None
    storage = server.banner.storage
    server.delete()
    if banner:
        transaction.on_commit(lambda: storage.delete(banner))


def _banner_webp(upload: UploadedFile) -> ContentFile:
    if upload.size and upload.size > BANNER_MAX_BYTES:
        raise _field_error("banner", "Банер має бути до 2 МБ.", code="banner_too_large")
    try:
        image = Image.open(upload)
        image_format = image.format
        image.load()
    except (UnidentifiedImageError, OSError) as error:
        raise _field_error(
            "banner", "Завантаж PNG, JPEG або WebP.", code="banner_invalid"
        ) from error
    if image_format not in {"PNG", "JPEG", "WEBP"}:
        raise _field_error("banner", "Завантаж PNG, JPEG або WebP.", code="banner_invalid")
    image = ImageOps.fit(ImageOps.exif_transpose(image).convert("RGB"), BANNER_SIZE)
    buffer = BytesIO()
    image.save(buffer, format="WEBP", quality=85)
    return ContentFile(buffer.getvalue(), name="banner.webp")


def set_banner(*, server: Server, user: User, upload: UploadedFile) -> Server:
    _check_owner(server, user)
    content = _banner_webp(upload)
    previous = server.banner.name if server.banner else None
    server.banner.save(content.name, content, save=False)
    server.save(update_fields=["banner", "updated_at"])
    if previous:
        server.banner.storage.delete(previous)
    return server


def remove_banner(*, server: Server, user: User) -> Server:
    _check_owner(server, user)
    if server.banner:
        server.banner.delete(save=False)
        server.save(update_fields=["banner", "updated_at"])
    return server


def record_ip_copy(*, server: Server) -> None:
    bump(server, "ip_copies_count")


# Pinging (Celery)

PINGED_STATUSES = (Server.Status.PUBLISHED, Server.Status.PENDING)


def _target(server: Server) -> clients.Target:
    return clients.Target(id=server.pk, host=server.host, port=server.port, edition=server.edition)


def record_pings(results: dict[int, clients.PingResult]) -> None:
    """Redis status for the API, a snapshot for the charts, `last_online_at` for sorting."""
    now = timezone.now()
    status.store(results)
    ServerSnapshot.objects.bulk_create(
        ServerSnapshot(
            server_id=pk,
            ts=now,
            is_online=result.is_online,
            players_online=result.players_online,
            players_max=result.players_max,
            latency_ms=result.latency_ms,
            version_name=result.version_name,
        )
        for pk, result in results.items()
    )
    online = [pk for pk, result in results.items() if result.is_online]
    Server.objects.filter(pk__in=online).update(last_online_at=now)


def ping_servers(
    servers: Iterable[Server], *, probe: Callable | None = None
) -> dict[int, clients.PingResult]:
    targets = [_target(server) for server in servers]
    if not targets:
        return {}
    results = asyncio.run(clients.ping_many(targets, probe=probe or clients.ping))
    record_pings(results)
    return results


def ping_all(*, batch_size: int = 200, probe: Callable | None = None) -> int:
    """Every listed server, in batches; returns how many were online."""
    queryset = Server.objects.filter(status__in=PINGED_STATUSES).only(
        "pk", "host", "port", "edition"
    )
    online, batch = 0, []
    for server in queryset.iterator(chunk_size=batch_size):
        batch.append(server)
        if len(batch) == batch_size:
            online += sum(r.is_online for r in ping_servers(batch, probe=probe).values())
            batch = []
    online += sum(r.is_online for r in ping_servers(batch, probe=probe).values())
    return online


# Verification: the owner puts the code into the MOTD


def request_verification(*, server: Server, user: User) -> str:
    if server.author_id != user.pk:
        raise DomainError(code="forbidden", message="Перевірити може лише власник.", status=403)
    if server.is_verified:
        return "verified"
    from . import tasks

    status.set_verification(server.pk, "checking")
    transaction.on_commit(lambda: tasks.verify_server.delay(server.pk))
    return "checking"


def verify(*, server_id: int, probe: Callable | None = None) -> str:
    """`verified` when the code is in the MOTD, else `missing` or `offline`."""
    server = Server.objects.filter(pk=server_id).first()
    if server is None:
        return "missing"
    result = asyncio.run((probe or clients.ping)(_target(server)))
    if not result.is_online:
        state = "offline"
    elif server.verify_code in result.motd.lower():
        Server.objects.filter(pk=server.pk).update(is_verified=True)
        state = "verified"
    else:
        state = "missing"
    status.set_verification(server.pk, state)
    return state
