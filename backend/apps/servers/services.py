"""Servers: mirrored from Modrinth, added and proved by owners, pinged every 5 minutes."""

import asyncio
import base64
import hmac
import logging
from collections.abc import Callable, Iterable
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.accounts.models import User
from apps.core.counters import bump
from apps.core.exceptions import DomainError
from apps.core.models import Source
from apps.moderation import services as moderation
from apps.moderation import words
from apps.mods.markdown import render_markdown
from apps.sources.clients import ping as clients
from apps.sources.clients.modrinth import ModrinthNotFoundError
from apps.sources.clients.modrinth_v3 import ModrinthV3Client
from apps.sources.runs import SyncCounter

from . import importers, status, validators
from .models import BEDROCK_PORT, JAVA_PORT, ContentKind, Server, ServerSnapshot

logger = logging.getLogger(__name__)

SNAPSHOT_DAYS = 30
SEARCH_PAGE = 20  # one v3 hit weighs up to 66 KB (docs/sources.md)


def _field_error(field: str, message: str, code: str = "invalid", status: int = 400) -> DomainError:
    return DomainError(code=code, message=message, fields={field: [message]}, status=status)


def _check_owner(server: Server, user: User) -> None:
    if server.owner_id != user.pk and not user.is_moderator:
        raise DomainError(code="forbidden", message="Це не твій сервер.", status=403)


def clean_address(*, address: str, edition: str) -> tuple[str, int]:
    """«play.example.com» or «play.example.com:25566»; the port defaults by edition."""
    host, port = validators.split_address(address)
    try:
        host = validators.clean_host(host)
        port = validators.clean_port(port or (BEDROCK_PORT if edition == "bedrock" else JAVA_PORT))
    except validators.AddressError as error:
        raise _field_error("address", str(error), code="invalid_address") from error
    return host, port


def _same_address(host: str, port: int, edition: str) -> Q:
    if edition == "bedrock":
        return Q(bedrock_host=host, bedrock_port=port)
    return Q(java_host=host, java_port=port)


def _target(server: Server) -> clients.Target:
    if server.java_host:
        return clients.Target(server.pk, server.java_host, server.java_port, "java")
    return clients.Target(server.pk, server.bedrock_host, server.bedrock_port, "bedrock")


# Owners

#: Unproven claims are pinged for a week; after that the player asks again
CLAIM_DAYS = 7


def claim_code(server_id: int, user_id: int) -> str:
    """The code a player puts into the MOTD: the same for them every time, different for
    everyone else, so nobody can reset or guess another player's code."""
    digest = hmac.new(
        settings.SECRET_KEY.encode(), f"server-claim:{server_id}:{user_id}".encode(), "sha256"
    ).digest()
    return "bc-" + base64.b32encode(digest).decode().lower()[:6]


def _claim(server: Server, user: User) -> Server:
    if server.owner_id == user.pk:
        return server
    if server.owner_id and server.is_verified:
        raise _field_error(
            "address", "У цього сервера вже є підтверджений власник.", code="server_owned"
        )
    server.claimant = user
    server.claimed_at = timezone.now()
    server.save(update_fields=["claimant", "claimed_at", "updated_at"])
    return server


def add_server(
    *, user: User, address: str, edition: str = "java", probe: Callable | None = None
) -> Server:
    """«Мій сервер»: the address must answer a ping; the player gets a code for the MOTD.

    A server already here (e.g. from Modrinth) is claimed the same way: whoever puts their
    code into its MOTD becomes its owner. The ping runs before any transaction is opened.
    """
    moderation.ensure_can_publish(user)
    host, port = clean_address(address=address, edition=edition)
    server = Server.objects.filter(_same_address(host, port, edition)).order_by("pk").first()
    if server is not None:
        return _claim(server, user)
    result = asyncio.run((probe or clients.ping)(clients.Target(0, host, port, edition)))
    if not result.is_online:
        raise _field_error(
            "address",
            "Сервер не відповідає. Перевір адресу й чи він увімкнений, і спробуй ще раз.",
            code="not_responding",
        )
    fields = (
        {"bedrock_host": host, "bedrock_port": port, "java_host": ""}
        if edition == "bedrock"
        else {"java_host": host, "java_port": port}
    )
    try:
        with transaction.atomic():
            server = Server.objects.create(
                source=Source.OWNER,
                external_id=f"{host}:{port}",
                name=host[:80],
                slug=importers.unique_slug(host),
                claimant=user,
                claimed_at=timezone.now(),
                supported_versions=[result.version_name[:32]] if result.version_name else [],
                **fields,
            )
    except IntegrityError:
        # Someone added the same address a moment ago
        server = Server.objects.get(source=Source.OWNER, external_id=f"{host}:{port}")
        return _claim(server, user)
    record_pings({server.pk: result})
    return server


def request_verification(*, server: Server, user: User) -> str:
    """Queues a check of this player's own code in the MOTD."""
    if server.owner_id == user.pk and server.is_verified:
        return "verified"
    if server.claimant_id != user.pk:
        raise DomainError(code="forbidden", message="Спершу додай цей сервер як свій.", status=403)
    from . import tasks

    status.set_verification(server.pk, user.pk, "checking")
    transaction.on_commit(lambda: tasks.verify_server.delay(server.pk, user.pk))
    return "checking"


def verify(*, server_id: int, user_id: int, probe: Callable | None = None) -> str:
    """`verified` when this player's code is in the MOTD (they become the owner), else
    `missing` or `offline`."""
    server = Server.objects.filter(pk=server_id).first()
    if server is None or (server.owner_id and server.is_verified):
        return "missing"
    result = asyncio.run((probe or clients.ping)(_target(server)))
    if not result.is_online:
        state = "offline"
    elif claim_code(server.pk, user_id) in result.motd.lower():
        server.is_verified = True
        server.owner_id = user_id
        if server.claimant_id == user_id:
            server.claimant = None
            server.claimed_at = None
        # save(), not update(): the search index listens to post_save
        server.save(update_fields=["is_verified", "owner", "claimant", "claimed_at", "updated_at"])
        state = "verified"
    else:
        state = "missing"
    status.set_verification(server.pk, user_id, state)
    return state


#: An owner of a Modrinth server writes about it here; what Modrinth knows stays its
OWNER_FIELDS = ("summary", "description_uk_md", "discord_url", "website_url", "required_pack")
#: A server added here has no source but its owner
OWN_SERVER_FIELDS = (
    "name",
    "languages",
    "country",
    "categories",
    "content_kind",
    "supported_versions",
    "recommended_version",
)


@transaction.atomic
def update_server(*, server: Server, user: User, data: dict) -> Server:
    _check_owner(server, user)
    words.check(
        name=data.get("name", ""),
        summary=data.get("summary", ""),
        description=data.get("description_uk_md", ""),
    )
    allowed = OWNER_FIELDS + (OWN_SERVER_FIELDS if server.source == Source.OWNER else ())
    changed = []
    previous_pack = server.required_pack_id
    for field in allowed:
        if field not in data:
            continue
        value = data[field]
        if field == "required_pack":
            value = _pack_for_joining(value, user)
        elif field == "country":
            value = value.strip().upper()[:2]
        elif isinstance(value, str):
            value = value.strip()
        setattr(server, field, value)
        changed.append(field)
    if "description_uk_md" in changed:
        server.description_uk_html = render_markdown(server.description_uk_md)
        changed.append("description_uk_html")
    if "required_pack" in changed and server.required_pack_id != previous_pack:
        # A pack the owner picked stays; clearing it gives the choice back to the sync
        server.pack_chosen_by_owner = server.required_pack_id is not None
        changed.append("pack_chosen_by_owner")
    if "required_pack" in changed and server.required_pack is not None:
        server.content_kind = ContentKind.MODDED
        changed.append("content_kind")
    if changed:
        server.save(update_fields=[*dict.fromkeys(changed), "updated_at"])
    return server


def _pack_for_joining(slug: str | None, user: User):
    """The owner's own pack or a Modrinth modpack, listed for everyone (guests take it
    from the server page); empty clears it."""
    from apps.packs.models import Origin
    from apps.packs.selectors import listed

    if not slug:
        return None
    pack = listed().filter(slug=slug).filter(Q(author=user) | Q(origin=Origin.MODRINTH)).first()
    if pack is None:
        raise _field_error(
            "required_pack",
            "Обери свою збірку, опубліковану для всіх, або модпак з Modrinth.",
            code="pack_not_found",
        )
    return pack


@transaction.atomic
def delete_server(*, server: Server, user: User) -> None:
    """Only servers added here; a Modrinth one is hidden by a moderator instead."""
    _check_owner(server, user)
    if server.source != Source.OWNER:
        raise DomainError(code="forbidden", message="Сервер з Modrinth не видаляється.", status=403)
    server.delete()


def record_ip_copy(*, server: Server) -> None:
    bump(server, "ip_copies_count")


# Modrinth


#: A server not seen in the search for this long is asked for directly
STALE_AFTER = timedelta(days=2)
#: …at most this many per run
STALE_PER_RUN = 50


def sync_modrinth(
    *,
    client: ModrinthV3Client,
    limit: int,
    run: SyncCounter,
    progress: Callable[[str], None] = logger.info,
) -> list[int]:
    """Ukrainian-speaking servers first, then the most relevant others, up to `limit`;
    then servers not refreshed for two days, asked one by one: gone from Modrinth → hidden.

    Returns ids of modded servers whose pack for joining must be imported (a task each).
    """
    ids: list[str] = []
    for language in ("uk", None):
        offset = 0
        while len(ids) < limit:
            page = client.search_servers(language=language, offset=offset, limit=SEARCH_PAGE)
            fresh = [hit.project_id for hit in page.hits if hit.project_id not in ids]
            ids.extend(fresh[: limit - len(ids)])
            offset += len(page.hits)
            if not page.hits or offset >= page.total_hits:
                break
    stale = list(
        Server.objects.visible()
        .filter(source=Source.MODRINTH, synced_at__lt=timezone.now() - STALE_AFTER)
        .exclude(external_id__in=ids)
        .order_by("synced_at")
        .values_list("external_id", flat=True)[:STALE_PER_RUN]
    )
    progress(f"servers: {len(ids)} found, {len(stale)} to recheck")
    packs: list[int] = []
    for project_id in [*ids, *stale]:
        with run.item(server=project_id):
            try:
                data = client.get_server(project_id)
            except ModrinthNotFoundError:
                hidden = importers.hide_gone(project_id)
                run.updated += hidden
                run.skipped += not hidden
                continue
            server, outcome = importers.import_server(data)
            setattr(run, outcome.value, getattr(run, outcome.value) + 1)
            if importers.needs_pack(server):
                packs.append(server.pk)
    return packs


def import_required_pack(*, server_id: int, client) -> bool:
    """The modpack Modrinth names for joining, as a Modrinth pack players can take.

    A pack uploaded into the server project belongs to that server alone and follows the
    version the server names. A separate modpack is one shared pack for the whole site
    (`packs.sync_official` keeps it at its newest release): the server links to it as it
    is, so servers and the daily sync never pull it between versions.
    """
    from apps.packs.models import Origin, Pack
    from apps.packs.services import import_modpack

    server = Server.objects.filter(pk=server_id).first()
    if server is None or not importers.needs_pack(server):
        return False
    own = server.modpack_project_id == server.external_id
    pack = None
    if not own:
        pack = Pack.objects.filter(
            origin=Origin.MODRINTH, external_id=server.modpack_project_id
        ).first()
    if pack is None:
        data = client.get_project(server.modpack_project_id)
        versions = client.get_versions_by_ids([server.modpack_version_id]) if own else []
        pack = import_modpack(client=client, data=data, version=versions[0] if versions else None)
        if pack is None:
            return False
        if own:
            # Its page on Modrinth is the server's one
            Pack.objects.filter(pk=pack.pk).update(external_url=server.external_url)
    Server.objects.filter(pk=server.pk).update(required_pack=pack)
    return True


# Pinging (Celery)


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
            version_name=result.version_name[:64],
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


def pinged() -> QuerySet[Server]:
    """Listed servers and the ones claimed during the last week (waiting for the code)."""
    recent = timezone.now() - timedelta(days=CLAIM_DAYS)
    return Server.objects.visible().filter(
        Q(source=Source.MODRINTH) | Q(is_verified=True) | Q(claimed_at__gte=recent)
    )


def ping_all(*, batch_size: int = 200, probe: Callable | None = None) -> int:
    """Every server in batches; returns how many were online."""
    queryset = pinged().only("pk", "java_host", "java_port", "bedrock_host", "bedrock_port")
    online, batch = 0, []
    for server in queryset.iterator(chunk_size=batch_size):
        batch.append(server)
        if len(batch) == batch_size:
            online += sum(r.is_online for r in ping_servers(batch, probe=probe).values())
            batch = []
    online += sum(r.is_online for r in ping_servers(batch, probe=probe).values())
    return online


def cleanup_snapshots(*, days: int = SNAPSHOT_DAYS) -> int:
    deleted, _ = ServerSnapshot.objects.filter(
        ts__lt=timezone.now() - timedelta(days=days)
    ).delete()
    return deleted
