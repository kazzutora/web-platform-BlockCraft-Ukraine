"""Modrinth → catalog: upserts by `(source, external_id)`, idempotent (tech.md 3, 6.3).

Field names come from the recorded answers in apps/sources/tests/fixtures/modrinth/.
"""

from collections.abc import Iterable
from enum import StrEnum

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.core.exceptions import DomainError
from apps.core.models import Source
from apps.sources.schemas import modrinth as schemas

from .categories import category_name_uk, gpu_load_for
from .markdown import render_markdown
from .models import Category, Project, ProjectType, ProjectVersion, Side

#: Loaders of a datapack-only project; anything else (fabric, forge…) makes it a mod
DATAPACK_LOADERS = frozenset({"datapack", "minecraft"})


class Outcome(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    #: Same page on Modrinth: only counters (downloads, follows) were refreshed
    UNCHANGED = "unchanged"


def project_type_of(data: schemas.ModrinthProject) -> str | None:
    """Our type of a Modrinth project, or None if the catalog does not take it.

    Modrinth reports datapacks as `mod` (docs/sources.md). A project whose files are all
    datapacks is a datapack; one that also ships a mod jar (Terralith) stays a mod and shows
    up in the datapack tab through its `datapack` loader (selectors.of_type).
    """
    if data.project_type == ProjectType.MOD:
        loaders = set(data.loaders)
        if "datapack" in loaders and loaders <= DATAPACK_LOADERS:
            return ProjectType.DATAPACK
        return ProjectType.MOD
    return data.project_type if data.project_type in ProjectType.values else None


def modrinth_url(project_type: str, slug: str) -> str:
    return f"https://modrinth.com/{project_type}/{slug}"


def upsert_categories(
    categories: Iterable[schemas.ModrinthCategory], *, project_type: str | None = None
) -> int:
    """Categories of our types with Ukrainian names; datapacks get a copy of mod categories.

    Modrinth has no categories of its own for datapacks: they are tagged with mod ones.
    """
    count = 0
    for item in categories:
        types = []
        if item.project_type in ProjectType.values:
            types.append(item.project_type)
        if item.project_type == ProjectType.MOD:
            types.append(ProjectType.DATAPACK)
        for category_type in types:
            if project_type and category_type != project_type:
                continue
            Category.objects.update_or_create(
                project_type=category_type,
                slug=item.name,
                defaults={"name_uk": category_name_uk(item.name), "header": item.header},
            )
            count += 1
    return count


def _side(value: str | None) -> str:
    return value if value in Side.values else Side.UNKNOWN


@transaction.atomic
def import_project(
    data: schemas.ModrinthProject, *, imported_by: User | None = None
) -> tuple[Project, Outcome]:
    """Creates or refreshes a project; never touches `is_hidden` (hidden stays hidden)."""
    project_type = project_type_of(data)
    if project_type is None:
        raise DomainError(code="unsupported_type", message="Цей тип проєктів не підтримується.")

    project = Project.objects.filter(source=Source.MODRINTH, external_id=data.id).first()
    counters = {
        "modrinth_downloads": data.downloads,
        "modrinth_follows": data.followers,
        "synced_at": timezone.now(),
    }
    if (
        project is not None
        and project.modrinth_updated_at == data.updated
        and project.slug == data.slug
        and project.project_type == project_type
    ):
        # `update()` skips post_save: the nightly reindex picks up the new counters
        Project.objects.filter(pk=project.pk).update(**counters)
        for name, value in counters.items():
            setattr(project, name, value)
        return project, Outcome.UNCHANGED

    outcome = Outcome.UPDATED
    if project is None:
        project = Project(source=Source.MODRINTH, external_id=data.id, imported_by=imported_by)
        outcome = Outcome.CREATED
    gallery = [
        {"url": image.url, "title": image.title or "", "featured": image.featured}
        for image in sorted(data.gallery, key=lambda image: (not image.featured, image.ordering))
    ]
    fields = {
        **counters,
        "slug": data.slug,
        "project_type": project_type,
        "external_url": modrinth_url(project_type, data.slug),
        "title": data.title[:128],
        "summary": data.description[:512],
        "body_html": render_markdown(data.body),
        "icon_url": data.icon_url or "",
        "gallery": gallery,
        "loaders": data.loaders,
        "game_versions": data.game_versions,
        "client_side": _side(data.client_side),
        "server_side": _side(data.server_side),
        "license": (data.license.name or data.license.id)[:128] if data.license else "",
        "source_url": data.source_url or "",
        "published_at": data.published,
        "modrinth_updated_at": data.updated,
    }
    for name, value in fields.items():
        setattr(project, name, value)
    if not project.gpu_load_manual and project_type == ProjectType.SHADER:
        project.gpu_load = gpu_load_for(data.categories + data.additional_categories)
    project.save()

    slugs = set(data.categories) | set(data.additional_categories)
    project.categories.set(Category.objects.filter(project_type=project_type, slug__in=slugs))
    return project, outcome


def _drop_missing(project: Project, seen: set[str], game_versions: Iterable[str] | None) -> None:
    from apps.packs.models import PackItem

    stale = project.versions.exclude(modrinth_version_id__in=seen)
    if game_versions is not None:
        asked = list(game_versions)
        in_packs = PackItem.objects.filter(version__in=stale).values("version_id")
        stale = stale.exclude(Q(pk__in=in_packs) & ~Q(game_versions__overlap=asked))
    stale.delete()


VERSION_FIELDS = (
    "name",
    "version_number",
    "version_type",
    "game_versions",
    "loaders",
    "date_published",
    "file_url",
    "file_name",
    "file_size",
    "sha1",
    "sha512",
    "dependencies",
)


def _dependencies(item: schemas.ModrinthVersion) -> list[dict]:
    """Always the same three keys; `version_id` stays null unless the author pinned one."""
    return [
        {
            "project_id": dependency.project_id,
            "version_id": dependency.version_id,
            "dependency_type": dependency.dependency_type,
        }
        for dependency in item.dependencies
        if dependency.project_id or dependency.version_id
    ]


def _version_values(item: schemas.ModrinthVersion, file: schemas.VersionFile) -> dict:
    return {
        "name": item.name[:256],
        "version_number": item.version_number[:128],
        "version_type": item.version_type
        if item.version_type in ProjectVersion.VersionType.values
        else ProjectVersion.VersionType.RELEASE,
        "game_versions": item.game_versions,
        "loaders": item.loaders,
        "date_published": item.date_published,
        "file_url": file.url,
        "file_name": file.filename[:256],
        "file_size": file.size,
        "sha1": file.hashes.get("sha1", ""),
        "sha512": file.hashes.get("sha512", ""),
        "dependencies": _dependencies(item),
    }


@transaction.atomic
def import_versions(
    project: Project,
    versions: Iterable[schemas.ModrinthVersion],
    *,
    game_versions: Iterable[str] | None = None,
) -> int:
    """Mirrors the given versions of a project in a fixed number of queries.

    `game_versions` is what the answer was asked for. A version missing from the answer is
    dropped if it was asked about (deleted on Modrinth); one for a game version we no
    longer ask about is kept while a pack still uses it, so the pack keeps its file.
    Returns how many versions the answer had.
    """
    known = {row.modrinth_version_id: row for row in project.versions.all()}
    new: list[ProjectVersion] = []
    changed: list[ProjectVersion] = []
    seen: set[str] = set()
    for item in versions:
        file = item.primary_file
        if file is None or item.id in seen:
            continue
        seen.add(item.id)
        values = _version_values(item, file)
        row = known.get(item.id)
        if row is None:
            new.append(ProjectVersion(project=project, modrinth_version_id=item.id, **values))
        elif any(getattr(row, name) != value for name, value in values.items()):
            for name, value in values.items():
                setattr(row, name, value)
            changed.append(row)
    ProjectVersion.objects.bulk_create(new, batch_size=200)
    ProjectVersion.objects.bulk_update(changed, VERSION_FIELDS, batch_size=200)
    _drop_missing(project, seen, game_versions)
    project.versions_synced_at = timezone.now()
    Project.objects.filter(pk=project.pk).update(versions_synced_at=project.versions_synced_at)
    return len(seen)
