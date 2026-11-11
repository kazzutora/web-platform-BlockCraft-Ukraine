"""Modrinth v3 server projects → `Server` (tech.md 8.2, docs/sources.md «Modrinth API v3»).

Field names follow the recorded answers in apps/sources/tests/fixtures/modrinth_v3/.
"""

import re
from enum import StrEnum
from urllib.parse import urlparse

from django.db import transaction
from django.utils import timezone

from apps.core.models import Source
from apps.core.text import slug_from
from apps.mods.markdown import render_markdown
from apps.sources.schemas.modrinth_v3 import ModpackContent, ServerProject, VanillaContent

from . import validators
from .models import JAVA_PORT, ContentKind, Server

#: Paths of the site a server slug must not take (/servers/add)
RESERVED_SLUGS = {"add", "new"}
_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)


class Outcome(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


def server_url(slug: str) -> str:
    return f"https://modrinth.com/server/{slug}"


def unique_slug(base: str, *, exclude_pk: int | None = None) -> str:
    base = (slug_from(base) or base)[:88] or "server"
    if base in RESERVED_SLUGS:
        base = f"{base}-server"
    slug, n = base, 2
    taken = Server.objects.exclude(pk=exclude_pk)
    while taken.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


def _banner(data: ServerProject) -> str:
    featured = [image for image in data.gallery if image.featured]
    images = featured or sorted(data.gallery, key=lambda image: image.ordering)
    return images[0].url if images else ""


def normalize_address(value: str) -> tuple[str, int]:
    """«http://Play.Example.com./» → ("play.example.com", 25565): as owners type it here."""
    value = _SCHEME.sub("", value.strip()).rstrip("/")
    host, port = validators.split_address(value)
    return host.lower().rstrip("."), port or JAVA_PORT


def _web_link(url: str) -> str:
    """Only http(s) links reach an `href`."""
    return url if urlparse(url).scheme in {"http", "https"} else ""


def _existing(data: ServerProject, host: str, port: int) -> Server | None:
    """This project, or the same address an owner added here before it came to Modrinth."""
    server = Server.objects.filter(source=Source.MODRINTH, external_id=data.id).first()
    if server is not None or not host:
        return server
    added = Server.objects.filter(
        source=Source.OWNER, java_host=host, java_port=port, is_hidden=False
    ).first()
    if added is not None:
        # One address — one server: it becomes the mirror, keeping its owner and history
        added.source = Source.MODRINTH
        added.external_id = data.id
        added.synced_at = None
    return added


@transaction.atomic
def import_server(data: ServerProject) -> tuple[Server, Outcome]:
    """Creates or refreshes a server; never touches `is_hidden`, nor what its owner wrote.

    An owner (who proved the address) keeps their summary, description, links and pack.
    """
    java = data.minecraft_java_server
    host, port = normalize_address(java.address)
    server = _existing(data, host, port)
    # Read after Modrinth's last change: only the play counter moves
    if server is not None and server.synced_at and server.synced_at >= data.updated:
        Server.objects.filter(pk=server.pk).update(
            modrinth_plays=java.verified_plays_2w or 0, synced_at=timezone.now()
        )
        return server, Outcome.UNCHANGED

    outcome = Outcome.UPDATED
    if server is None:
        server = Server(
            source=Source.MODRINTH,
            external_id=data.id,
            slug=unique_slug(data.slug),
            is_verified=False,
        )
        outcome = Outcome.CREATED
    content = java.content
    server.name = data.name[:80]
    server.external_url = server_url(data.slug)
    server.java_host, server.java_port = host, port
    server.country = (data.minecraft_server.country or "").upper()[:2]
    server.languages = [code.lower()[:8] for code in data.minecraft_server.languages]
    server.categories = [category[:48] for category in data.categories]
    server.description_html = render_markdown(data.description)
    server.icon_url = data.icon_url or ""
    server.banner_url = _banner(data)
    server.modrinth_plays = java.verified_plays_2w or 0
    server.synced_at = timezone.now()
    if isinstance(content, VanillaContent):
        server.content_kind = ContentKind.VANILLA
        server.supported_versions = content.supported_game_versions
        server.recommended_version = content.recommended_game_version or ""
        server.modpack_project_id = server.modpack_version_id = ""
    elif isinstance(content, ModpackContent):
        server.content_kind = ContentKind.MODDED
        server.supported_versions = []
        server.recommended_version = ""
        server.modpack_project_id = content.project_id
        server.modpack_version_id = content.version_id
    if server.pack_chosen_by_owner and server.required_pack_id:
        # The owner named the pack to join with: the server needs mods whatever Modrinth says
        server.content_kind = ContentKind.MODDED
    elif server.content_kind == ContentKind.VANILLA:
        server.required_pack = None
    if server.owner_id is None:
        links = data.link_urls
        server.summary = data.summary[:280]
        server.discord_url = _web_link(links["discord"].url) if "discord" in links else ""
        server.website_url = _web_link(links["site"].url) if "site" in links else ""
    server.save()
    return server, outcome


def needs_pack(server: Server) -> bool:
    """A modded server whose pack for joining is missing or not the one Modrinth names.

    A pack uploaded into the server project follows the version the server names; a
    separate modpack only has to be the same project (it is shared, see
    `services.import_required_pack`). A pack the owner picked is left alone.
    """
    if server.content_kind != ContentKind.MODDED or not server.modpack_project_id:
        return False
    if server.pack_chosen_by_owner:
        return False
    pack = server.required_pack
    if pack is None or pack.external_id != server.modpack_project_id:
        return True
    own = server.modpack_project_id == server.external_id
    return own and pack.modrinth_version_id != server.modpack_version_id


def hide_gone(project_id: str) -> bool:
    """Modrinth no longer has the project: it leaves the catalog."""
    return bool(
        Server.objects.filter(
            source=Source.MODRINTH, external_id=project_id, is_hidden=False
        ).update(is_hidden=True, hidden_reason="Сервер зник з Modrinth.")
    )
