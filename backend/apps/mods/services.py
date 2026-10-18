import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.accounts.models import User
from apps.core.exceptions import DomainError
from apps.library.models import Download

from . import schemas
from .categories import category_name_uk, gpu_load_for
from .clients import ModrinthClient
from .markdown import render_markdown
from .models import Category, Project, ProjectType, ProjectVersion

logger = logging.getLogger(__name__)

SUPPORTED_TYPES = {choice.value for choice in ProjectType}
BATCH = 100


@dataclass
class SyncResult:
    categories: int = 0
    projects: dict[str, int] = field(default_factory=dict)
    versions: int = 0


def upsert_categories(categories: Iterable[schemas.ModrinthCategory]) -> int:
    count = 0
    for item in categories:
        if item.project_type not in SUPPORTED_TYPES:
            continue
        Category.objects.update_or_create(
            project_type=item.project_type,
            slug=item.name,
            defaults={"name_uk": category_name_uk(item.name), "header": item.header},
        )
        count += 1
    return count


@transaction.atomic
def upsert_project(
    data: schemas.ModrinthProject,
    *,
    new_status: str = Project.Status.PUBLISHED,
    suggested_by: User | None = None,
) -> Project:
    """Creates or refreshes a project from Modrinth; moderation status of known ones is kept."""
    if data.project_type not in SUPPORTED_TYPES:
        raise DomainError(code="unsupported_type", message="Цей тип проєктів не підтримується.")

    gallery = [
        {"url": image.url, "title": image.title or "", "featured": image.featured}
        for image in sorted(data.gallery, key=lambda image: (not image.featured, image.ordering))
    ]
    defaults = {
        "slug": data.slug,
        "project_type": data.project_type,
        "title": data.title[:128],
        "summary": data.description[:512],
        "body_md": data.body,
        "body_html": render_markdown(data.body),
        "icon_url": data.icon_url or "",
        "gallery": gallery,
        "loaders": data.loaders,
        "game_versions": data.game_versions,
        "license": (data.license.name or data.license.id)[:128] if data.license else "",
        "source_url": data.source_url or "",
        "modrinth_downloads": data.downloads,
        "modrinth_updated_at": data.updated,
        "synced_at": timezone.now(),
    }
    project = Project.objects.filter(modrinth_id=data.id).first()
    if project is None:
        project = Project(modrinth_id=data.id, status=new_status, suggested_by=suggested_by)
        if new_status == Project.Status.PUBLISHED:
            project.published_at = data.published
    for name, value in defaults.items():
        setattr(project, name, value)
    if not project.gpu_load_manual and data.project_type == ProjectType.SHADER:
        project.gpu_load = gpu_load_for(data.categories + data.additional_categories)
    project.save()

    slugs = set(data.categories) | set(data.additional_categories)
    project.categories.set(Category.objects.filter(project_type=data.project_type, slug__in=slugs))
    return project


@transaction.atomic
def replace_versions(project: Project, versions: Iterable[schemas.ModrinthVersion]) -> int:
    """Stores the given Modrinth versions of a project and drops the ones no longer listed."""
    seen: list[str] = []
    for item in versions:
        file = item.primary_file
        if file is None:
            continue
        ProjectVersion.objects.update_or_create(
            modrinth_version_id=item.id,
            defaults={
                "project": project,
                "name": item.name[:256],
                "version_number": item.version_number[:128],
                "version_type": item.version_type
                if item.version_type in ProjectVersion.VersionType.values
                else ProjectVersion.VersionType.RELEASE,
                "game_versions": item.game_versions,
                "loaders": item.loaders,
                "file_url": file.url,
                "file_name": file.filename[:256],
                "file_size": file.size,
                "sha1": file.hashes.get("sha1", ""),
                "dependencies": [
                    dependency.model_dump(exclude_none=True) for dependency in item.dependencies
                ],
                "released_at": item.date_published,
            },
        )
        seen.append(item.id)
    project.versions.exclude(modrinth_version_id__in=seen).delete()
    return len(seen)


def sync_project_versions(
    *, client: ModrinthClient, project: Project, game_versions: Iterable[str]
) -> int:
    versions = client.get_versions(project.modrinth_id, game_versions=list(game_versions))
    return replace_versions(project, versions)


def sync_popular(
    *,
    client: ModrinthClient,
    limits: dict[str, int],
    game_versions: list[str],
    progress: Callable[[str], None] = logger.info,
) -> SyncResult:
    """Top-N projects of every type by downloads, with their versions for supported releases.

    Idempotent: running it again only refreshes data.
    """
    result = SyncResult(categories=upsert_categories(client.get_categories()))
    for project_type, limit in limits.items():
        ids: list[str] = []
        offset = 0
        while len(ids) < limit:
            page = client.search(
                project_type=project_type,
                game_versions=game_versions,
                offset=offset,
                limit=min(BATCH, limit - len(ids)),
            )
            ids.extend(hit.project_id for hit in page.hits)
            offset += len(page.hits)
            if not page.hits or offset >= page.total_hits:
                break
        progress(f"{project_type}: {len(ids)} projects found")

        synced = 0
        for start in range(0, len(ids), BATCH):
            for data in client.get_projects(ids[start : start + BATCH]):
                project = upsert_project(data)
                result.versions += sync_project_versions(
                    client=client, project=project, game_versions=game_versions
                )
                synced += 1
            progress(f"{project_type}: {synced}/{len(ids)} synced")
        result.projects[project_type] = synced
    return result


def import_suggested(
    *, client: ModrinthClient, slug: str, suggested_by: User | None, game_versions: list[str]
) -> Project:
    """A player suggested a Modrinth project: it waits for moderation as `pending`."""
    existing = Project.objects.filter(slug=slug).first()
    if existing:
        return existing
    project = upsert_project(
        client.get_project(slug), new_status=Project.Status.PENDING, suggested_by=suggested_by
    )
    sync_project_versions(client=client, project=project, game_versions=game_versions)
    return project


def publish(*, project: Project) -> Project:
    project.status = Project.Status.PUBLISHED
    project.published_at = project.published_at or timezone.now()
    project.rejection_reason = ""
    project.save(update_fields=["status", "published_at", "rejection_reason"])
    return project


@transaction.atomic
def record_download(
    *,
    project: Project,
    version: ProjectVersion,
    user: User | None,
    game_version: str = "",
    loader: str = "",
) -> None:
    Project.objects.filter(pk=project.pk).update(downloads_count=F("downloads_count") + 1)
    if user is not None and user.is_authenticated:
        Download.objects.create(
            user=user,
            project=project,
            version=version,
            game_version=game_version[:32],
            loader=loader[:32],
        )
