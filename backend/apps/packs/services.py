import json
import logging
import re
import secrets
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import Count, Max
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import ValidationError

from apps.accounts.models import User
from apps.core.counters import bump
from apps.core.exceptions import DomainError
from apps.core.game import GAME_VERSIONS
from apps.core.text import slug_from
from apps.core.versions import latest_release
from apps.moderation import services as moderation
from apps.moderation import words
from apps.mods.markdown import render_markdown
from apps.mods.models import Project, ProjectType, ProjectVersion
from apps.mods.selectors import dependencies_of, resolve_version
from apps.mods.services import import_missing
from apps.sources.clients.modrinth import ModrinthClient, ModrinthError
from apps.sources.schemas.modrinth import ModrinthProject, ModrinthVersion, VersionFile

from . import selectors
from .choices import MAX_ITEMS, MAX_STYLES, MRPACK_LOADER_KEYS, PackLoader, Style
from .models import LoaderRelease, Pack, PackItem
from .schemas import MrpackIndex

logger = logging.getLogger(__name__)

COVER_SIZE = (1200, 630)
COVER_MAX_BYTES = 2 * 1024 * 1024
#: A pack of one mod is just that mod
MIN_ITEMS_TO_PUBLISH = 2
#: Changing these makes every file pick again
TARGET_FIELDS = ("game_version", "loader")
TEXT_FIELDS = ("title", "summary", "gpu_note", "install_md", "changelog_md", "loader_version")
FOLDERS = {
    ProjectType.MOD: "mods",
    ProjectType.RESOURCEPACK: "resourcepacks",
    ProjectType.SHADER: "shaderpacks",
}

COPY = {
    "forbidden": "Це не твоя зборка.",
    "not_found": "Такого мода немає в каталозі.",
    "already_added": "Цей мод уже в зборці.",
    "too_many": f"У зборці може бути до {MAX_ITEMS} модів.",
    "no_version": "У «{title}» немає файлу для {game_version} · {loader}.",
    "not_in_pack": "Цього мода немає в зборці.",
    "too_few": "Додай хоча б два моди, щоб опублікувати зборку.",
    "unresolved": "Для деяких модів немає файлу під цю версію — прибери їх або зміни версію гри.",
    "already_published": "Зборку вже надіслано.",
    "styles": f"Обери до {MAX_STYLES} стилів.",
    "cover_size": "Обкладинка має бути до 2 МБ.",
    "cover_type": "Завантаж PNG, JPEG або WebP.",
    "no_loader_version": "Ще не знаємо версію лоадера для цієї зборки. Вкажи її в налаштуваннях.",
    "official_edit": "Офіційні зборки оновлюються з Modrinth, їх не можна змінювати.",
}


def _error(code: str, *, field: str | None = None, status: int = 400, **params) -> DomainError:
    message = COPY[code].format(**params)
    return DomainError(
        code=code, message=message, fields={field: [message]} if field else None, status=status
    )


def _check_owner(pack: Pack, user: User) -> None:
    if pack.author_id != user.pk and not user.is_moderator:
        raise _error("forbidden", status=403)
    if pack.is_official:
        raise _error("official_edit", status=403)


def unique_slug(title: str) -> str:
    base = (slug_from(title) or f"pack-{secrets.token_hex(3)}")[:88]
    slug, n = base, 2
    taken = Pack.objects.all()
    while taken.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


def clean_styles(styles: Iterable[str]) -> list[str]:
    unique = list(dict.fromkeys(styles))
    if len(unique) > MAX_STYLES:
        raise _error("styles", field="style_tags")
    return unique


def _check_words(data: dict) -> None:
    words.check(
        **{field: data.get(field, "") for field in TEXT_FIELDS if field != "loader_version"}
    )


def _apply_text(pack: Pack, data: dict) -> list[str]:
    changed = []
    for field in TEXT_FIELDS:
        if field in data:
            setattr(pack, field, data[field].strip())
            changed.append(field)
    for field in ("install", "changelog"):
        if f"{field}_md" in data:
            setattr(pack, f"{field}_html", render_markdown(getattr(pack, f"{field}_md")))
            changed.append(f"{field}_html")
    return changed


@transaction.atomic
def create_pack(*, author: User, data: dict) -> Pack:
    """A draft: the author fills it in the constructor and publishes it with `publish_pack`."""
    moderation.ensure_can_publish(author)
    _check_words(data)
    pack = Pack(
        author=author,
        slug=unique_slug(data["title"]),
        game_version=data["game_version"],
        loader=data["loader"],
        style_tags=clean_styles(data.get("style_tags", [])),
        ram_min_gb=data.get("ram_min_gb", 4),
        status=Pack.Status.DRAFT,
    )
    _apply_text(pack, data)
    pack.save()
    return pack


@transaction.atomic
def update_pack(*, pack: Pack, user: User, data: dict) -> Pack:
    _check_owner(pack, user)
    _check_words(data)
    changed = _apply_text(pack, data)
    if "style_tags" in data:
        pack.style_tags = clean_styles(data["style_tags"])
        changed.append("style_tags")
    if "ram_min_gb" in data:
        pack.ram_min_gb = data["ram_min_gb"]
        changed.append("ram_min_gb")
    retarget = any(field in data and data[field] != getattr(pack, field) for field in TARGET_FIELDS)
    for field in TARGET_FIELDS:
        if field in data:
            setattr(pack, field, data[field])
            changed.append(field)
    if changed:
        pack.save(update_fields=[*changed, "updated_at"])
    if retarget:
        repick_versions(pack)
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
def publish_pack(*, pack: Pack, user: User) -> Pack:
    """Draft (or rejected) → published; reports and the word filter moderate afterwards."""
    _check_owner(pack, user)
    moderation.ensure_can_publish(user)
    if pack.status not in (Pack.Status.DRAFT, Pack.Status.REJECTED):
        raise _error("already_published")
    items = list(pack.items.all())
    # Dependencies do not count: «Sodium + Fabric API» is still one mod
    if sum(not item.added_as_dependency for item in items) < MIN_ITEMS_TO_PUBLISH:
        raise _error("too_few")
    if any(item.version_id is None for item in items):
        raise _error("unresolved")
    pack.status = Pack.Status.PUBLISHED
    pack.rejection_reason = ""
    if pack.published_at is None:
        pack.published_at = timezone.now()
    pack.save(update_fields=["status", "rejection_reason", "published_at", "updated_at"])
    return pack


# Items


def _pick(pack: Pack, project: Project) -> ProjectVersion | None:
    return resolve_version(project=project, game_version=pack.game_version, loader=pack.loader)


def _next_position(pack: Pack) -> int:
    return (pack.items.aggregate(top=Max("position"))["top"] or 0) + 1


def _touch(pack: Pack) -> None:
    pack.save(update_fields=["updated_at"])


def complete_dependencies(pack: Pack, versions: Iterable[ProjectVersion] | None = None) -> int:
    """Adds required dependencies of `versions` (all files by default), recursively.

    Dependencies missing from our catalog are left for `tasks.fill_dependencies`; ones without
    a file for the pack's version show up in `selectors.inspect`.
    """
    if versions is None:
        versions = [item.version for item in pack.items.select_related("version") if item.version]
    queue = list(versions)
    present = set(pack.items.values_list("project__modrinth_id", flat=True))
    position = _next_position(pack)
    added = 0
    while queue:
        for dependency in dependencies_of(queue.pop()):
            project = dependency.project
            if dependency.dependency_type != "required" or project is None:
                continue
            if project.modrinth_id in present:
                continue
            version = _pick(pack, project)
            if version is None:
                continue
            PackItem.objects.create(
                pack=pack,
                project=project,
                version=version,
                added_as_dependency=True,
                position=position,
            )
            present.add(project.modrinth_id)
            queue.append(version)
            position += 1
            added += 1
    return added


def prune_dependencies(pack: Pack) -> int:
    """Removes items that were only there as dependencies of something no longer in the pack."""
    removed = 0
    while True:
        items = list(pack.items.select_related("project", "version"))
        needed = {
            dependency.get("project_id")
            for item in items
            if item.version
            for dependency in item.version.dependencies
            if dependency.get("dependency_type") == "required"
        }
        orphans = [
            item.pk
            for item in items
            if item.added_as_dependency and item.project.modrinth_id not in needed
        ]
        if not orphans:
            return removed
        removed += PackItem.objects.filter(pk__in=orphans).delete()[0]


def _queue_fill(pack: Pack) -> None:
    from . import tasks

    if selectors.missing_dependency_ids(pack):
        transaction.on_commit(lambda: tasks.fill_dependencies.delay(pack.pk))


@transaction.atomic
def add_item(*, pack: Pack, user: User, project_slug: str) -> PackItem:
    """Adds a project with the file for the pack's version and loader, plus its dependencies."""
    _check_owner(pack, user)
    project = Project.objects.published().filter(slug=project_slug).first()
    if project is None:
        raise _error("not_found", field="project", status=404)
    item = pack.items.filter(project=project).first()
    if item is not None:
        if not item.added_as_dependency:
            raise _error("already_added", field="project")
        # The author picked a mod that was already pulled in: now it is theirs
        item.added_as_dependency = False
        item.save(update_fields=["added_as_dependency"])
        return item
    if pack.items.count() >= MAX_ITEMS:
        raise _error("too_many", field="project")
    version = _pick(pack, project)
    if version is None:
        raise _error(
            "no_version",
            field="project",
            title=project.title,
            game_version=pack.game_version,
            loader=pack.get_loader_display(),
        )
    item = PackItem.objects.create(
        pack=pack, project=project, version=version, position=_next_position(pack)
    )
    complete_dependencies(pack, [version])
    _queue_fill(pack)
    _touch(pack)
    return item


@transaction.atomic
def update_item(*, pack: Pack, user: User, project_slug: str, is_required: bool) -> PackItem:
    _check_owner(pack, user)
    item = pack.items.filter(project__slug=project_slug).first()
    if item is None:
        raise _error("not_in_pack", status=404)
    item.is_required = is_required
    item.save(update_fields=["is_required"])
    _touch(pack)
    return item


@transaction.atomic
def remove_item(*, pack: Pack, user: User, project_slug: str) -> None:
    _check_owner(pack, user)
    deleted, _ = pack.items.filter(project__slug=project_slug).delete()
    if not deleted:
        raise _error("not_in_pack", status=404)
    prune_dependencies(pack)
    _touch(pack)


def repick_versions(pack: Pack) -> None:
    """After a game version or loader change: new files, then dependencies of the new files."""
    for item in pack.items.select_related("project"):
        version = _pick(pack, item.project)
        if version != item.version:
            item.version = version
            item.save(update_fields=["version"])
    complete_dependencies(pack)
    prune_dependencies(pack)
    _queue_fill(pack)


@transaction.atomic
def fork_pack(*, pack: Pack, user: User) -> Pack:
    """A draft copy the player can change; the original counts its forks."""
    moderation.ensure_can_publish(user)
    copy = Pack.objects.create(
        author=user,
        title=pack.title,
        slug=unique_slug(pack.title),
        summary=pack.summary,
        style_tags=pack.style_tags,
        game_version=pack.game_version,
        loader=pack.loader,
        loader_version=pack.loader_version or selectors.loader_version(pack),
        ram_min_gb=pack.ram_min_gb,
        gpu_note=pack.gpu_note,
        install_md=pack.install_md,
        install_html=pack.install_html,
        forked_from=pack,
        status=Pack.Status.DRAFT,
    )
    PackItem.objects.bulk_create(
        PackItem(
            pack=copy,
            project_id=item.project_id,
            version_id=item.version_id,
            is_required=item.is_required,
            added_as_dependency=item.added_as_dependency,
            position=item.position,
        )
        for item in pack.items.all()
    )
    bump(pack, "forks_count")
    return copy


# Cover


def _cover_webp(upload: UploadedFile) -> ContentFile:
    if upload.size and upload.size > COVER_MAX_BYTES:
        raise _error("cover_size", field="cover")
    try:
        image = Image.open(upload)
        image_format = image.format
        image.load()
    except (UnidentifiedImageError, OSError) as error:
        raise _error("cover_type", field="cover") from error
    if image_format not in {"PNG", "JPEG", "WEBP"}:
        raise _error("cover_type", field="cover")
    image = ImageOps.fit(ImageOps.exif_transpose(image).convert("RGB"), COVER_SIZE)
    buffer = BytesIO()
    image.save(buffer, format="WEBP", quality=85)
    return ContentFile(buffer.getvalue(), name="cover.webp")


def set_cover(*, pack: Pack, user: User, upload: UploadedFile) -> Pack:
    _check_owner(pack, user)
    content = _cover_webp(upload)
    previous = pack.cover.name if pack.cover else None
    pack.cover.save(content.name, content, save=False)
    pack.save(update_fields=["cover", "updated_at"])
    if previous:
        pack.cover.storage.delete(previous)
    return pack


def remove_cover(*, pack: Pack, user: User) -> Pack:
    _check_owner(pack, user)
    if pack.cover:
        pack.cover.delete(save=False)
        pack.save(update_fields=["cover", "updated_at"])
    return pack


# .mrpack


def mrpack_index(pack: Pack) -> dict:
    """modrinth.index.json (formatVersion 1): files stay on Modrinth's CDN."""
    loader_version = selectors.loader_version(pack)
    if not loader_version:
        raise _error("no_loader_version", status=409)
    files = []
    for item in pack.items.select_related("project", "version"):
        version = item.version
        if version is None or not version.sha1:
            continue
        hashes = {"sha1": version.sha1}
        if version.sha512:
            hashes["sha512"] = version.sha512
        file = {
            "path": f"{FOLDERS.get(item.project.project_type, 'mods')}/{version.file_name}",
            "hashes": hashes,
            "downloads": [version.file_url],
            "fileSize": version.file_size,
        }
        if not item.is_required:
            file["env"] = {"client": "optional", "server": "optional"}
        files.append(file)
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


def recount_forks(pack_ids: Iterable[int]) -> None:
    """After forks went away in bulk (a deleted account): count what is left."""
    for pack in Pack.objects.filter(pk__in=set(pack_ids)).annotate(left=Count("forks")):
        Pack.objects.filter(pk=pack.pk).update(forks_count=pack.left)


# Official packs (popular Modrinth modpacks)

OFFICIAL_EMAIL = "official@blockcraft.invalid"
OFFICIAL_NICKNAME = "BlockCraft"
INDEX_NAME = "modrinth.index.json"
#: The index lists files only; a bigger one is not a modpack we can show
INDEX_MAX_BYTES = 5 * 1024 * 1024
CDN_FILE = re.compile(
    r"^https://cdn\.modrinth\.com/data/(?P<project>[A-Za-z0-9]+)/versions/(?P<version>[A-Za-z0-9]+)/"
)
# Modrinth modpack categories → our styles
MODRINTH_STYLES = {
    "optimization": Style.PERFORMANCE,
    "technology": Style.TECH,
    "magic": Style.MAGIC,
    "adventure": Style.ADVENTURE,
    "quests": Style.QUESTS,
    "multiplayer": Style.MULTIPLAYER,
    "lightweight": Style.LIGHTWEIGHT,
}


def official_author() -> User:
    """The account official packs belong to; nobody can sign in as it (no password)."""
    user = User.objects.filter(email=OFFICIAL_EMAIL).first()
    if user is None:
        user = User.objects.create_user(email=OFFICIAL_EMAIL, nickname=OFFICIAL_NICKNAME)
    return user


def pick_modpack_version(versions: Iterable[ModrinthVersion]) -> ModrinthVersion | None:
    """The newest release for a loader and game version we support."""
    supported = [
        version
        for version in versions
        if set(version.loaders) & set(PackLoader.values)
        and set(version.game_versions) & set(GAME_VERSIONS)
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
    is_required: bool


def file_refs(index: MrpackIndex) -> list[FileRef]:
    """Modrinth-hosted files a player needs (server-only files are skipped)."""
    refs = []
    for file in index.files:
        env = file.env
        if env is not None and env.client == "unsupported":
            continue
        match = next(filter(None, (CDN_FILE.match(url) for url in file.downloads)), None)
        if match is None:
            continue
        refs.append(
            FileRef(
                project_id=match["project"],
                version_id=match["version"],
                is_required=env is None or env.client != "optional",
            )
        )
    return refs


def import_modpack(*, client: ModrinthClient, data: ModrinthProject) -> Pack | None:
    """Creates or refreshes the official pack of a Modrinth modpack; None if unsupported.

    Only the index of the modpack's .mrpack is read, to learn its files; nothing is stored,
    players download the original from Modrinth (`source_file_url`).
    """
    version = pick_modpack_version(client.get_versions(data.id, game_versions=list(GAME_VERSIONS)))
    if version is None or version.primary_file is None:
        return None
    pack = Pack.objects.filter(modrinth_id=data.id).first()
    if pack is not None and pack.modrinth_version_id == version.id:
        Pack.objects.filter(pk=pack.pk).update(modrinth_downloads=data.downloads)
        return pack

    index = read_index(client=client, file=version.primary_file)
    refs = file_refs(index)
    import_missing(
        client=client,
        modrinth_ids={ref.project_id for ref in refs},
        game_versions=list(GAME_VERSIONS),
    )
    with transaction.atomic():
        return _store_official(pack=pack, data=data, version=version, index=index, refs=refs)


def _store_official(
    *,
    pack: Pack | None,
    data: ModrinthProject,
    version: ModrinthVersion,
    index: MrpackIndex,
    refs: list[FileRef],
) -> Pack:
    loader = next(loader for loader in version.loaders if loader in PackLoader.values)
    game_version = latest_release([gv for gv in version.game_versions if gv in GAME_VERSIONS])
    if pack is None:
        pack = Pack(
            author=official_author(),
            slug=unique_slug(data.slug),
            modrinth_id=data.id,
            is_official=True,
            status=Pack.Status.PUBLISHED,
            published_at=data.published,
        )
    styles = dict.fromkeys(
        MODRINTH_STYLES[category] for category in data.categories if category in MODRINTH_STYLES
    )
    pack.title = data.title[:80]
    pack.summary = data.description[:280]
    pack.icon_url = data.icon_url or ""
    pack.style_tags = list(styles)[:MAX_STYLES]
    pack.game_version = game_version
    pack.loader = loader
    pack.loader_version = index.dependencies.get(MRPACK_LOADER_KEYS[loader], "")[:64]
    pack.changelog_md = (version.changelog or "")[:5000]
    pack.changelog_html = render_markdown(pack.changelog_md)
    pack.modrinth_version_id = version.id
    pack.source_file_url = version.primary_file.url if version.primary_file else ""
    pack.modrinth_downloads = data.downloads

    projects = {
        project.modrinth_id: project
        for project in Project.objects.published().filter(
            modrinth_id__in={ref.project_id for ref in refs}
        )
    }
    files = {
        row.modrinth_version_id: row
        for row in ProjectVersion.objects.filter(
            modrinth_version_id__in={ref.version_id for ref in refs}
        )
    }
    items: dict[int, PackItem] = {}
    for position, ref in enumerate(refs, start=1):
        project = projects.get(ref.project_id)
        if project is None or project.pk in items:
            continue
        file = files.get(ref.version_id)
        if file is None or file.project_id != project.pk:
            file = resolve_version(project=project, game_version=game_version, loader=loader)
        items[project.pk] = PackItem(
            project=project, version=file, is_required=ref.is_required, position=position
        )
    # More files take more memory: a rough floor for the requirements block
    pack.ram_min_gb = 4 if len(items) < 100 else 6 if len(items) < 200 else 8
    pack.save()
    pack.items.all().delete()
    for item in items.values():
        item.pack = pack
    PackItem.objects.bulk_create(items.values())
    return pack


def import_popular_modpacks(*, client: ModrinthClient, limit: int) -> list[str]:
    """The `limit` most downloaded modpacks for supported versions, as official packs."""
    page = client.search(project_type="modpack", game_versions=GAME_VERSIONS, limit=limit)
    imported = []
    for data in client.get_projects([hit.project_id for hit in page.hits]):
        try:
            pack = import_modpack(client=client, data=data)
        except (DomainError, ModrinthError):
            logger.warning("Could not import modpack %s", data.slug, exc_info=True)
            continue
        if pack is not None:
            imported.append(pack.slug)
    return imported


def fill_dependencies(*, client: ModrinthClient, pack: Pack) -> int:
    """Imports the pack's missing dependencies from Modrinth, then adds them to the pack."""
    missing = selectors.missing_dependency_ids(pack)
    if not missing:
        return 0
    import_missing(client=client, modrinth_ids=missing, game_versions=list(GAME_VERSIONS))
    with transaction.atomic():
        return complete_dependencies(pack)


def store_loader_releases(found: dict[tuple[str, str], str]) -> int:
    for (loader, game_version), version in found.items():
        LoaderRelease.objects.update_or_create(
            loader=loader, game_version=game_version, defaults={"version": version}
        )
    return len(found)
