"""Packs: community packs built with the compatibility engine, Modrinth modpacks mirrored.

A community pack stores what its author asked for (`reason=requested`); dependencies and
shader engines are whatever `compat.resolve` says at the moment, with reasons. Every change
of the set or the target rebuilds the items and keeps the resolution as `compat_report`.
"""

import json
import logging
import re
import secrets
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from io import BytesIO
from urllib.parse import urlsplit

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Count, Max
from django.utils import timezone
from PIL import Image, UnidentifiedImageError
from pydantic import ValidationError

from apps.accounts.models import User
from apps.compat import operations
from apps.compat import services as compat
from apps.compat.serializers import resolution_data
from apps.compat.types import Status, Target
from apps.core.counters import bump
from apps.core.exceptions import DomainError
from apps.core.models import Source
from apps.core.text import slug_from
from apps.core.versions import latest_release
from apps.moderation import services as moderation
from apps.moderation import words
from apps.mods import importers
from apps.mods.markdown import render_markdown
from apps.mods.models import Project, ProjectType, ProjectVersion
from apps.mods.services import import_missing
from apps.sources.clients.modrinth import CDN_HOST, ModrinthClient, ModrinthError
from apps.sources.runs import SyncCounter
from apps.sources.schemas.modrinth import ModrinthProject, ModrinthVersion, VersionFile
from apps.sources.services import supported_game_versions

from . import selectors
from .choices import MAX_ITEMS, MRPACK_LOADER_KEYS, PackLoader
from .models import CompatStatus, Env, Origin, Pack, PackExternalFile, PackItem, Reason, Visibility
from .schemas import MrpackIndex

logger = logging.getLogger(__name__)

#: A pack of one mod is just that mod
MIN_ITEMS_TO_PUBLISH = 2
#: Changing these makes every file pick again
TARGET_FIELDS = ("game_version", "loader")
TEXT_FIELDS = ("title", "summary", "notes_md", "loader_version")
#: Where launchers put each type; datapacks go into a world, not into the .mrpack
FOLDERS = {
    ProjectType.MOD: "mods",
    ProjectType.RESOURCEPACK: "resourcepacks",
    ProjectType.SHADER: "shaderpacks",
}

COPY = {
    "forbidden": "Це не твоя збірка.",
    "not_found": "Такого проєкту немає в каталозі.",
    "already_added": "Цей проєкт уже в збірці.",
    "too_many": f"У збірці може бути до {MAX_ITEMS} проєктів.",
    "not_in_pack": "Цього проєкту немає в збірці.",
    "needed": "Його потребує «{by}» — прибери спершу те, що від нього залежить.",
    "too_few": "Додай хоча б два проєкти, щоб опублікувати збірку.",
    "pack_has_errors": "У збірці є проблеми сумісності — виправ їх перед публікацією.",
    "not_checked": "Збірку ще перевіряємо: залежності довантажуються з Modrinth.",
    "no_loader_version": "Ще не знаємо версію лоадера для цієї збірки. Вкажи її в налаштуваннях.",
    "official_edit": "Збірки з Modrinth оновлюються звідти, їх не можна змінювати.",
    "too_big_to_copy": f"У збірці понад {MAX_ITEMS} проєктів — її не скопіювати й не перенести.",
    "invalid_mrpack": "Це не схоже на modrinth.index.json.",
}


def _error(code: str, *, field: str | None = None, status: int = 400, **params) -> DomainError:
    message = COPY[code].format(**params)
    return DomainError(
        code=code, message=message, fields={field: [message]} if field else None, status=status
    )


def _check_owner(pack: Pack, user: User) -> None:
    if pack.is_modrinth:
        raise _error("official_edit", status=403)
    if pack.author_id != user.pk and not user.is_moderator:
        raise _error("forbidden", status=403)


def unique_slug(title: str) -> str:
    base = (slug_from(title) or f"pack-{secrets.token_hex(3)}")[:88]
    slug, n = base, 2
    while Pack.objects.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


def _check_words(data: dict) -> None:
    words.check(**{field: data.get(field, "") for field in ("title", "summary", "notes_md")})


def _apply_text(pack: Pack, data: dict) -> list[str]:
    changed = []
    for field in TEXT_FIELDS:
        if field in data:
            setattr(pack, field, data[field].strip())
            changed.append(field)
    if "notes_md" in data:
        pack.notes_html = render_markdown(pack.notes_md)
        changed.append("notes_html")
    return changed


def target_of(pack: Pack) -> Target:
    return Target(pack.game_version, pack.loader)


# The set and its check


@dataclass(frozen=True)
class Check:
    before: str
    after: str


def _store_report(pack: Pack, data: dict) -> Check:
    before = pack.compat_status
    status = data["status"]
    pack.compat_status = CompatStatus.UNKNOWN if status == Status.INCOMPLETE else status
    pack.compat_report = data
    pack.compat_checked_at = timezone.now()
    Pack.objects.filter(pk=pack.pk).update(
        compat_status=pack.compat_status,
        compat_report=data,
        compat_checked_at=pack.compat_checked_at,
    )
    return Check(before, pack.compat_status)


def requested(pack: Pack) -> list[PackItem]:
    return list(
        pack.items.filter(reason=Reason.REQUESTED).select_related("project").order_by("position")
    )


@transaction.atomic
def rebuild(pack: Pack) -> Check:
    """Re-resolves the author's set for the pack's target and rewrites the items to match.

    Requested items keep their place and env; dependencies and engines come and go with the
    resolution. Files are the newest that fit: a community pack follows its projects.
    """
    asked = requested(pack)
    resolved = compat.resolve(
        items=[(item.project, None) for item in asked], target=target_of(pack)
    )
    rows = resolved.projects
    by_slug = {row.slug: row for row in rows.values()}
    versions = {
        row.modrinth_version_id: row
        for row in ProjectVersion.objects.filter(
            modrinth_version_id__in={
                item.version.id for item in resolved.resolution.items if item.version
            }
        )
    }
    current = {item.project_id: item for item in pack.items.all()}
    keep: set[int] = set()
    new: list[PackItem] = []
    changed: list[PackItem] = []
    position = max((item.position for item in asked), default=0)
    for entry in resolved.resolution.items:
        project = by_slug.get(entry.project.slug)
        if project is None or project.pk in keep:
            continue
        keep.add(project.pk)
        version = versions.get(entry.version.id) if entry.version else None
        item = current.get(project.pk)
        if item is None:
            position += 1
            item = PackItem(pack=pack, project=project, position=position)
            new.append(item)
        else:
            changed.append(item)
        item.version = version
        item.reason = entry.reason.value
        item.required_by = entry.required_by
    pack.items.exclude(project_id__in=keep).delete()
    PackItem.objects.bulk_update(changed, ["version", "reason", "required_by"], batch_size=200)
    PackItem.objects.bulk_create(new, batch_size=200)
    pack.items_count = len(keep)
    Pack.objects.filter(pk=pack.pk).update(items_count=pack.items_count)
    return _store_report(pack, resolution_data(resolved))


def recheck(pack: Pack) -> Check:
    """The nightly check. A community pack follows its projects: it is resolved again, so a
    dependency whose file left Modrinth is replaced or reported, never silently dropped
    from the .mrpack. A Modrinth modpack is checked as its author shipped it (`trust_pins`).
    """
    if not pack.is_modrinth:
        return rebuild(pack)
    items = list(pack.items.select_related("project", "version"))
    resolved = compat.resolve(
        items=[
            (item.project, item.version.modrinth_version_id if item.version else None)
            for item in items
            if item.reason == Reason.REQUESTED or pack.is_modrinth
        ],
        target=target_of(pack),
        trust_pins=pack.is_modrinth,
    )
    return _store_report(pack, resolution_data(resolved))


def check(pack: Pack) -> dict:
    """`GET /packs/{slug}/check`: the stored report, refreshed while it waits for imports."""
    if pack.compat_status == CompatStatus.UNKNOWN or not pack.compat_report:
        if pack.is_modrinth or pack.status == Pack.Status.PUBLISHED:
            recheck(pack)
        else:
            rebuild(pack)
    return pack.compat_report


# Community packs


@transaction.atomic
def create_pack(*, author: User, data: dict) -> Pack:
    """A draft: the author fills it in the constructor and publishes it with `publish_pack`."""
    moderation.ensure_can_publish(author)
    _check_words(data)
    pack = Pack(
        author=author,
        origin=Origin.COMMUNITY,
        slug=unique_slug(data["title"]),
        game_version=data["game_version"],
        loader=data["loader"],
        ram_min_gb=data.get("ram_min_gb", 4),
        visibility=data.get("visibility", Visibility.PUBLIC),
        status=Pack.Status.DRAFT,
    )
    _apply_text(pack, data)
    pack.save()
    return pack


def _lock(pack: Pack) -> None:
    """One change of a pack at a time: two adds sharing a dependency would clash."""
    Pack.objects.select_for_update().filter(pk=pack.pk).first()


@transaction.atomic
def update_pack(*, pack: Pack, user: User, data: dict) -> Pack:
    _check_owner(pack, user)
    _lock(pack)
    _check_words(data)
    old_loader_version = pack.loader_version
    changed = _apply_text(pack, data)
    for field in ("ram_min_gb", "visibility"):
        if field in data:
            setattr(pack, field, data[field])
            changed.append(field)
    retarget = any(field in data and data[field] != getattr(pack, field) for field in TARGET_FIELDS)
    for field in TARGET_FIELDS:
        if field in data:
            setattr(pack, field, data[field])
            changed.append(field)
    if retarget and pack.loader_version == old_loader_version:
        # A Forge / NeoForge build belongs to its game version: start from the latest one
        pack.loader_version = ""
        changed.append("loader_version")
    if changed:
        pack.save(update_fields=[*dict.fromkeys(changed), "updated_at"])
    if retarget:
        rebuild(pack)
    return pack


@transaction.atomic
def delete_pack(*, pack: Pack, user: User) -> None:
    _check_owner(pack, user)
    if pack.forked_from_id:
        bump(pack.forked_from, "forks_count", -1)
    cover = pack.cover.name if pack.cover else None
    storage = pack.cover.storage
    pack.delete()
    if cover:
        transaction.on_commit(lambda: storage.delete(cover))


@transaction.atomic
def publish_pack(*, pack: Pack, user: User, visibility: str | None = None) -> Pack:
    """Draft → published («усім» or «за посиланням»); a pack with errors cannot go out."""
    _check_owner(pack, user)
    moderation.ensure_can_publish(user)
    if sum(1 for _ in requested(pack)) < MIN_ITEMS_TO_PUBLISH:
        raise _error("too_few")
    result = check(pack)
    if result.get("status") == Status.INCOMPLETE:
        raise _error("not_checked", status=409)
    if pack.compat_status == CompatStatus.ERRORS:
        raise _error("pack_has_errors")
    if visibility:
        pack.visibility = visibility
    pack.status = Pack.Status.PUBLISHED
    pack.rejection_reason = ""
    if pack.published_at is None:
        pack.published_at = timezone.now()
    pack.save(
        update_fields=["status", "visibility", "rejection_reason", "published_at", "updated_at"]
    )
    _queue_cover(pack)
    return pack


def _touch(pack: Pack) -> None:
    pack.save(update_fields=["updated_at"])


@transaction.atomic
def add_item(*, pack: Pack, user: User, project_slug: str) -> PackItem:
    """Adds a project the author picked; its dependencies come with the rebuild."""
    _check_owner(pack, user)
    _lock(pack)
    project = Project.objects.visible().filter(slug=project_slug).first()
    if project is None:
        raise _error("not_found", field="project", status=404)
    item = pack.items.filter(project=project).first()
    if item is not None:
        if item.reason == Reason.REQUESTED:
            raise _error("already_added", field="project")
        # The author picked a project that was already pulled in: now it is theirs
        item.reason = Reason.REQUESTED
        item.save(update_fields=["reason"])
    else:
        if pack.items.count() >= MAX_ITEMS:
            raise _error("too_many", field="project")
        top = pack.items.aggregate(top=Max("position"))["top"] or 0
        item = PackItem.objects.create(pack=pack, project=project, position=top + 1)
    rebuild(pack)
    _touch(pack)
    _queue_cover(pack)
    item.refresh_from_db()
    return item


@transaction.atomic
def update_item(*, pack: Pack, user: User, project_slug: str, optional: bool) -> PackItem:
    """«Необов'язковий»: launchers offer the file instead of installing it."""
    _check_owner(pack, user)
    _lock(pack)
    item = pack.items.filter(project__slug=project_slug).first()
    if item is None:
        raise _error("not_in_pack", status=404)
    item.env_client = item.env_server = Env.OPTIONAL if optional else Env.REQUIRED
    item.save(update_fields=["env_client", "env_server"])
    _touch(pack)
    return item


@transaction.atomic
def remove_item(*, pack: Pack, user: User, project_slug: str) -> None:
    _check_owner(pack, user)
    _lock(pack)
    item = pack.items.filter(project__slug=project_slug).first()
    if item is None:
        raise _error("not_in_pack", status=404)
    if item.reason != Reason.REQUESTED:
        raise _error("needed", field="project", by=", ".join(item.required_by))
    item.delete()
    rebuild(pack)
    _touch(pack)
    _queue_cover(pack)


def retarget_preview(*, pack: Pack, game_version: str, loader: str) -> operations.Retarget:
    """«Копія під 26.1»: what stays, changes, falls out and joins — nothing is saved."""
    asked = requested(pack) if not pack.is_modrinth else list(pack.items.select_related("project"))
    if len(asked) > MAX_ITEMS:
        raise _error("too_big_to_copy")
    resolved = compat.resolve(
        items=[(item.project, None) for item in asked], target=Target(game_version, loader)
    )
    current = [
        operations.Current(
            item.project.slug, item.version.modrinth_version_id if item.version else None
        )
        for item in pack.items.select_related("project", "version")
    ]
    return operations.retarget(current, resolved.resolution)


@transaction.atomic
def fork_pack(*, pack: Pack, user: User, game_version: str = "", loader: str = "") -> Pack:
    """A draft copy, for the same game or straight away for another one."""
    moderation.ensure_can_publish(user)
    source = pack.items.all() if pack.is_modrinth else pack.items.filter(reason=Reason.REQUESTED)
    if source.count() > MAX_ITEMS:
        raise _error("too_big_to_copy")
    copy = Pack.objects.create(
        author=user,
        origin=Origin.COMMUNITY,
        title=pack.title,
        slug=unique_slug(pack.title),
        summary=pack.summary,
        game_version=game_version or pack.game_version,
        loader=loader or pack.loader,
        loader_version="" if game_version or loader else pack.loader_version,
        ram_min_gb=pack.ram_min_gb,
        notes_md=pack.notes_md,
        notes_html=pack.notes_html,
        forked_from=pack,
        status=Pack.Status.DRAFT,
    )
    # A Modrinth modpack has no «requested» layer: every file becomes the author's pick
    PackItem.objects.bulk_create(
        PackItem(
            pack=copy,
            project_id=item.project_id,
            version_id=item.version_id,
            env_client=item.env_client,
            env_server=item.env_server,
            position=item.position,
        )
        for item in source
    )
    rebuild(copy)
    bump(pack, "forks_count")
    return copy


def recount_forks(pack_ids: Iterable[int]) -> None:
    """After forks went away in bulk (a deleted account): count what is left."""
    for pack in Pack.objects.filter(pk__in=set(pack_ids)).annotate(left=Count("forks")):
        Pack.objects.filter(pk=pack.pk).update(forks_count=pack.left)


# Cover: a mosaic of the first icons (players upload nothing)

COVER_SIZE = 600
COVER_ICONS = 4


def _queue_cover(pack: Pack) -> None:
    from . import tasks

    transaction.on_commit(lambda: tasks.render_cover.delay(pack.pk))


def cover_icons(pack: Pack) -> list[str]:
    items = pack.items.select_related("project").order_by("position")
    picked = [item.project.icon_url for item in items if item.reason == Reason.REQUESTED]
    return [url for url in picked if url][:COVER_ICONS]


def render_cover(*, client: ModrinthClient, pack: Pack) -> bool:
    """2×2 icons on the paper colour; fewer icons — fewer tiles. Old cover is replaced."""
    urls = cover_icons(pack)
    tiles = []
    for url in urls:
        try:
            tiles.append(Image.open(BytesIO(client.image(url))).convert("RGBA"))
        except (ModrinthError, UnidentifiedImageError, OSError):
            logger.info("Icon %s skipped for the cover of pack %s", url, pack.pk)
    if not tiles:
        return False
    canvas = Image.new("RGB", (COVER_SIZE, COVER_SIZE), (244, 241, 234))
    columns = 1 if len(tiles) == 1 else 2
    rows = 1 if len(tiles) <= 2 else 2
    cell_w, cell_h = COVER_SIZE // columns, COVER_SIZE // rows
    for index, tile in enumerate(tiles):
        side = int(min(cell_w, cell_h) * 0.7)
        tile = tile.resize(
            (side, side), Image.Resampling.NEAREST if tile.width <= 64 else Image.Resampling.LANCZOS
        )
        x = (index % columns) * cell_w + (cell_w - side) // 2
        y = (index // columns) * cell_h + (cell_h - side) // 2
        canvas.paste(tile, (x, y), tile)
    buffer = BytesIO()
    canvas.save(buffer, format="WEBP", quality=85)
    previous = pack.cover.name if pack.cover else None
    pack.cover.save("cover.webp", ContentFile(buffer.getvalue()), save=False)
    Pack.objects.filter(pk=pack.pk).update(cover=pack.cover.name)
    if previous:
        pack.cover.storage.delete(previous)
    return True


# .mrpack


def mrpack_index(pack: Pack) -> dict:
    """modrinth.index.json (formatVersion 1): files stay on Modrinth's CDN."""
    loader_version = selectors.loader_version(pack)
    if not loader_version:
        raise _error("no_loader_version", status=409)
    files = []
    for item in pack.items.select_related("project", "version"):
        version = item.version
        folder = FOLDERS.get(item.project.project_type)
        if version is None or folder is None or not version.sha1:
            continue
        if urlsplit(version.file_url).hostname != CDN_HOST:
            continue  # .mrpack downloads may point only at Modrinth (docs/sources.md)
        hashes = {"sha1": version.sha1}
        if version.sha512:
            hashes["sha512"] = version.sha512
        files.append(
            {
                "path": f"{folder}/{version.file_name}",
                "hashes": hashes,
                "env": {"client": item.env_client, "server": item.env_server},
                "downloads": [version.file_url],
                "fileSize": version.file_size,
            }
        )
    return {
        "formatVersion": 1,
        "game": "minecraft",
        "versionId": pack.updated_at.strftime("%Y.%m.%d.%H%M"),
        "name": pack.title,
        "summary": pack.summary,
        "files": files,
        "dependencies": {
            "minecraft": pack.game_version,
            MRPACK_LOADER_KEYS[pack.loader]: loader_version,
        },
    }


def export_mrpack(*, pack: Pack) -> bytes:
    """The .mrpack (a zip with the index only) and +1 to the pack's downloads."""
    index = mrpack_index(pack)
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("modrinth.index.json", json.dumps(index, ensure_ascii=False, indent=2))
    record_download(pack=pack)
    return buffer.getvalue()


def record_download(*, pack: Pack) -> None:
    bump(pack, "downloads_count")


# Modrinth modpacks

OFFICIAL_EMAIL = "official@blockcraft.invalid"
OFFICIAL_NICKNAME = "BlockCraft"
INDEX_NAME = "modrinth.index.json"
#: The index lists files only; a bigger one is not a modpack we can show
INDEX_MAX_BYTES = 5 * 1024 * 1024
CDN_FILE = re.compile(
    r"^https://cdn\.modrinth\.com/data/(?P<project>[A-Za-z0-9]+)/versions/(?P<version>[A-Za-z0-9]+)/"
)


def official_author() -> User:
    """The account Modrinth modpacks belong to; nobody can sign in as it (no password)."""
    user = User.objects.filter(email=OFFICIAL_EMAIL).first()
    if user is None:
        user = User.objects.create_user(email=OFFICIAL_EMAIL, nickname=OFFICIAL_NICKNAME)
    return user


def pick_modpack_version(versions: Iterable[ModrinthVersion]) -> ModrinthVersion | None:
    """The newest release for a loader and game version we support."""
    game_versions = set(supported_game_versions())
    supported = [
        version
        for version in versions
        if set(version.loaders) & set(PackLoader.values)
        and set(version.game_versions) & game_versions
        and version.primary_file
    ]
    releases = [version for version in supported if version.version_type == "release"]
    return max(releases or supported, key=lambda version: version.date_published, default=None)


def read_index(*, client: ModrinthClient, file: VersionFile) -> MrpackIndex:
    """modrinth.index.json of a modpack file; the rest of the archive (configs) is not read."""
    try:
        raw = client.read_zip_member(
            file.url, size=file.size, name=INDEX_NAME, max_bytes=INDEX_MAX_BYTES
        )
        return MrpackIndex.model_validate_json(raw)
    except (zipfile.BadZipFile, KeyError, ValidationError) as error:
        raise DomainError(code="invalid_mrpack", message="Це не схоже на .mrpack.") from error


@dataclass(frozen=True)
class FileRef:
    project_id: str
    version_id: str
    env_client: str
    env_server: str


@dataclass
class IndexFiles:
    refs: list[FileRef]
    #: Files that are not Modrinth projects: kept as they are
    external: list[dict]


def _env(value: str | None) -> str:
    return value if value in Env.values else Env.REQUIRED


def index_files(*, client: ModrinthClient | None, index: MrpackIndex) -> IndexFiles:
    """Splits an index: Modrinth files (by CDN link, else by sha1) and the rest.

    Hashes are asked from Modrinth in one request; without a client only links count.
    """
    refs: list[FileRef] = []
    unknown = []
    for file in index.files:
        env = file.env
        client_env = _env(env.client if env else None)
        server_env = _env(env.server if env else None)
        match = next(filter(None, (CDN_FILE.match(url) for url in file.downloads)), None)
        if match is not None:
            refs.append(FileRef(match["project"], match["version"], client_env, server_env))
        else:
            unknown.append((file, client_env, server_env))
    found: dict[str, ModrinthVersion] = {}
    hashes = [file.hashes.get("sha1", "") for file, _, _ in unknown if file.hashes.get("sha1")]
    if client is not None and hashes:
        found = client.versions_by_hashes(hashes)
    external = []
    for file, client_env, server_env in unknown:
        version = found.get(file.hashes.get("sha1", ""))
        if version is not None:
            refs.append(FileRef(version.project_id, version.id, client_env, server_env))
            continue
        external.append(
            {
                "path": file.path[:300],
                "url": (file.downloads[0] if file.downloads else "")[:700],
                "sha1": file.hashes.get("sha1", "")[:40],
                "sha512": file.hashes.get("sha512", "")[:128],
                "size": file.fileSize,
            }
        )
    return IndexFiles(refs, external)


def import_modpack(
    *, client: ModrinthClient, data: ModrinthProject, version: ModrinthVersion | None = None
) -> Pack | None:
    """Creates or refreshes the pack of a Modrinth modpack; None if unsupported.

    Only the index of the modpack's .mrpack is read, to learn its files; nothing is stored,
    players download the original from Modrinth (`source_file_url`). `version` pins one
    (a server names the exact pack to join with); otherwise the newest release is taken.
    """
    # A pinned version passes the same checks: a loader and a game version we support
    candidates = (
        [version]
        if version is not None
        else client.get_versions(data.id, game_versions=supported_game_versions())
    )
    version = pick_modpack_version(candidates)
    if version is None or version.primary_file is None:
        return None
    pack = Pack.objects.filter(origin=Origin.MODRINTH, external_id=data.id).first()
    if pack is not None and pack.modrinth_version_id == version.id:
        Pack.objects.filter(pk=pack.pk).update(
            modrinth_downloads=data.downloads, synced_at=timezone.now()
        )
        return pack

    index = read_index(client=client, file=version.primary_file)
    files = index_files(client=client, index=index)
    import_missing(
        client=client,
        modrinth_ids={ref.project_id for ref in files.refs},
        game_versions=supported_game_versions(),
    )
    _store_versions(client=client, refs=files.refs)
    with transaction.atomic():
        pack = _store_modrinth(pack=pack, data=data, version=version, index=index, files=files)
    recheck(pack)
    return pack


def _store_versions(*, client: ModrinthClient, refs: list[FileRef]) -> None:
    """Modpacks pin exact files; ones outside our supported versions are fetched by id."""
    wanted = {ref.version_id for ref in refs}
    have = set(
        ProjectVersion.objects.filter(modrinth_version_id__in=wanted).values_list(
            "modrinth_version_id", flat=True
        )
    )
    missing = sorted(wanted - have)
    if not missing:
        return
    projects = {
        row.external_id: row
        for row in Project.objects.filter(
            source=Source.MODRINTH, external_id__in={ref.project_id for ref in refs}
        )
    }
    for start in range(0, len(missing), 100):
        for item in client.get_versions_by_ids(missing[start : start + 100]):
            project = projects.get(item.project_id)
            file = item.primary_file
            if project is None or file is None:
                continue
            ProjectVersion.objects.update_or_create(
                modrinth_version_id=item.id,
                defaults={"project": project, **importers.version_values(item, file)},
            )


def _store_modrinth(
    *,
    pack: Pack | None,
    data: ModrinthProject,
    version: ModrinthVersion,
    index: MrpackIndex,
    files: IndexFiles,
) -> Pack:
    loader = next(loader for loader in version.loaders if loader in PackLoader.values)
    supported = set(supported_game_versions())
    # The index says what the pack was built for; the version's list may be wider
    built_for = index.dependencies.get("minecraft", "")
    game_version = (
        built_for
        if built_for in supported
        else latest_release([gv for gv in version.game_versions if gv in supported])
    )
    if pack is None:
        pack = Pack(
            author=official_author(),
            origin=Origin.MODRINTH,
            slug=unique_slug(data.slug),
            external_id=data.id,
            status=Pack.Status.PUBLISHED,
            visibility=Visibility.PUBLIC,
            published_at=data.published,
        )
    pack.title = data.title[:80]
    pack.summary = data.description[:280]
    pack.description_html = render_markdown(data.body)
    pack.icon_url = data.icon_url or ""
    pack.external_url = f"https://modrinth.com/modpack/{data.slug}"
    pack.game_version = game_version
    pack.loader = loader
    pack.loader_version = index.dependencies.get(MRPACK_LOADER_KEYS[loader], "")[:64]
    pack.modrinth_version_id = version.id
    pack.source_file_url = version.primary_file.url if version.primary_file else ""
    pack.modrinth_downloads = data.downloads
    pack.synced_at = timezone.now()

    projects = {
        project.external_id: project
        for project in Project.objects.filter(
            source=Source.MODRINTH, external_id__in={ref.project_id for ref in files.refs}
        )
    }
    versions = {
        row.modrinth_version_id: row
        for row in ProjectVersion.objects.filter(
            modrinth_version_id__in={ref.version_id for ref in files.refs}
        )
    }
    items: dict[int, PackItem] = {}
    for position, ref in enumerate(files.refs, start=1):
        project = projects.get(ref.project_id)
        if project is None or project.pk in items:
            continue
        file = versions.get(ref.version_id)
        items[project.pk] = PackItem(
            project=project,
            version=file if file and file.project_id == project.pk else None,
            reason=Reason.REQUESTED,
            env_client=ref.env_client,
            env_server=ref.env_server,
            position=position,
        )
    pack.items_count = len(items)
    # More files take more memory: a rough floor for the requirements block
    pack.ram_min_gb = 4 if len(items) < 100 else 6 if len(items) < 200 else 8
    pack.save()
    pack.items.all().delete()
    for item in items.values():
        item.pack = pack
    PackItem.objects.bulk_create(items.values())
    pack.external_files.all().delete()
    PackExternalFile.objects.bulk_create(
        PackExternalFile(pack=pack, **values)
        for values in {value["path"]: value for value in files.external}.values()
    )
    return pack


SEARCH_PAGE = 100  # Modrinth's maximum `limit`


def import_popular_modpacks(
    *, client: ModrinthClient, limit: int, run: SyncCounter | None = None
) -> list[str]:
    """The `limit` most downloaded modpacks for supported versions, as Modrinth packs."""
    run = run if run is not None else SyncCounter()
    game_versions = supported_game_versions()
    ids: list[str] = []
    while len(ids) < limit:
        page = client.search(
            project_type="modpack",
            game_versions=game_versions,
            offset=len(ids),
            limit=min(SEARCH_PAGE, limit - len(ids)),
        )
        ids.extend(hit.project_id for hit in page.hits)
        if not page.hits or len(ids) >= page.total_hits:
            break
    imported = []
    for start in range(0, len(ids), SEARCH_PAGE):
        for data in client.get_projects(ids[start : start + SEARCH_PAGE]):
            existing = Pack.objects.filter(origin=Origin.MODRINTH, external_id=data.id).first()
            before = existing.modrinth_version_id if existing else None
            with run.item(modpack=data.slug):
                pack = import_modpack(client=client, data=data)
                if pack is None:
                    run.skipped += 1
                    continue
                if existing is None:
                    run.created += 1
                elif before == pack.modrinth_version_id:
                    run.unchanged += 1
                else:
                    run.updated += 1
                imported.append(pack.slug)
    return imported


def store_loader_releases(found: dict[tuple[str, str], str]) -> int:
    from .models import LoaderRelease

    for (loader, game_version), version in found.items():
        LoaderRelease.objects.update_or_create(
            loader=loader, game_version=game_version, defaults={"version": version}
        )
    return len(found)


# /import → «Зберегти як збірку»


def import_draft(*, author: User, data: dict) -> Pack:
    """A draft from a player's `mods` folder (hashes) or a .mrpack's index.

    Every identified project becomes the author's pick; the target is the index's game,
    the one given, or the guess. Files we cannot identify are left out (they stay with
    the player).
    """
    from apps.mods.identify import identify

    index = data.get("index")
    hashes: list[str] = [item["hash"] for item in data.get("files", [])]
    game_version, loader = data.get("game_version", ""), data.get("loader", "")
    title = data.get("title", "")
    if index is not None:
        try:
            parsed = MrpackIndex.model_validate(index)
        except ValidationError as error:
            raise _error("invalid_mrpack", field="index") from error
        hashes = [file.hashes["sha1"] for file in parsed.files if file.hashes.get("sha1")]
        game_version = game_version or parsed.dependencies.get("minecraft", "")
        loader = loader or next(
            (key for key, name in MRPACK_LOADER_KEYS.items() if name in parsed.dependencies), ""
        )
        title = title or parsed.name
    found = identify(hashes)
    guess = found.guess.target
    if not game_version and guess:
        game_version = guess.game_version
    if not loader and guess and guess.loader in PackLoader.values:
        loader = guess.loader
    if game_version not in set(supported_game_versions()) or loader not in PackLoader.values:
        raise DomainError(
            code="unknown_target",
            message="Не вдалося визначити версію гри й лоадер — вкажи їх.",
            fields={"game_version": ["Обери версію гри й лоадер."]},
        )
    with transaction.atomic():
        pack = create_pack(
            author=author,
            data={
                "title": (title or "Мої моди")[:80],
                "game_version": game_version,
                "loader": loader,
                "visibility": Visibility.PRIVATE,
            },
        )
        projects = []
        for row in found.known.values():
            if row.project.is_hidden:
                continue  # taken out by a moderator: not offered as a pick
            if row.project_id not in {project.pk for project in projects}:
                projects.append(row.project)
        PackItem.objects.bulk_create(
            PackItem(pack=pack, project=project, position=position)
            for position, project in enumerate(projects[:MAX_ITEMS], start=1)
        )
        rebuild(pack)
    _queue_cover(pack)
    return pack
