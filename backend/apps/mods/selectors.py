from dataclasses import dataclass

from django.contrib.auth.models import AnonymousUser
from django.db.models import Case, IntegerField, Q, QuerySet, Value, When
from django.http import Http404

from apps.core.game import GameContext, Loader
from apps.core.kinds import Viewer, get_kind
from apps.core.versions import is_release, latest_release, nearest_versions
from apps.social.selectors import with_viewer_state

from .models import Project, ProjectType, ProjectVersion

# Loaders matter only for mods: resource packs use "minecraft", shaders "iris"/"optifine"
LOADER_AWARE_TYPES = {ProjectType.MOD}


def of_type(project_type: str) -> Q:
    """A tab of the catalog. Mods that also ship as a datapack (Terralith) are in both."""
    if project_type == ProjectType.DATAPACK:
        return Q(project_type=ProjectType.DATAPACK) | Q(
            project_type=ProjectType.MOD, loaders__contains=["datapack"]
        )
    return Q(project_type=project_type)


def for_loader(loader: str) -> Q:
    """Only mods depend on the loader; a vanilla game takes mods that ship as datapacks."""
    if not loader:
        return Q()
    wanted = "datapack" if loader == Loader.VANILLA else loader
    return ~Q(project_type=ProjectType.MOD) | Q(loaders__contains=[wanted])


def fits_game(project: Project, game: GameContext | None) -> bool | None:
    """Whether the project has files for «Моя гра»; None when the viewer chose nothing.

    Same rule as the catalog filters (project-level versions and loaders), so a card in
    the filtered catalog never says it does not fit.
    """
    if game is None or not game.is_set:
        return None
    if game.game_version and game.game_version not in project.game_versions:
        return False
    if game.loader and project.project_type in LOADER_AWARE_TYPES:
        wanted = "datapack" if game.loader == Loader.VANILLA else game.loader
        return wanted in project.loaders
    return True


def catalog(viewer: Viewer | None = None) -> QuerySet[Project]:
    """Visible projects with the viewer's favorite/review state annotated."""
    queryset = Project.objects.visible().prefetch_related("categories")
    return with_viewer_state(queryset, viewer=viewer or AnonymousUser(), kind=get_kind("mod"))


def get_project(*, slug: str, viewer: Viewer | None = None) -> Project:
    try:
        return catalog(viewer).get(slug=slug)
    except Project.DoesNotExist as error:
        raise Http404 from error


def versions_for(
    *, project: Project, game_version: str = "", loader: str = ""
) -> QuerySet[ProjectVersion]:
    """Versions that fit the game version and loader: releases first, newest first."""
    queryset = project.versions.all()
    if game_version:
        queryset = queryset.filter(game_versions__contains=[game_version])
    if loader and project.project_type in LOADER_AWARE_TYPES:
        wanted = "datapack" if loader == Loader.VANILLA else loader
        queryset = queryset.filter(loaders__contains=[wanted])
    return queryset.annotate(
        stability=Case(
            When(version_type=ProjectVersion.VersionType.RELEASE, then=Value(0)),
            When(version_type=ProjectVersion.VersionType.BETA, then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        )
    ).order_by("stability", "-date_published")


def resolve_version(
    *, project: Project, game_version: str, loader: str = ""
) -> ProjectVersion | None:
    """The file to download for «26.3 · Fabric»: the newest release, else the newest beta/alpha."""
    return versions_for(project=project, game_version=game_version, loader=loader).first()


def nearest_game_versions(
    *, project: Project, game_version: str, loader: str = "", limit: int = 3
) -> list[str]:
    """Game versions that do have a file for this loader, closest to the requested one."""
    queryset = versions_for(project=project, loader=loader)
    available = {
        version
        for row in queryset.values_list("game_versions", flat=True)
        for version in row
        if is_release(version)
    }
    return nearest_versions(game_version, list(available), limit=limit)


def latest_game_version(project: Project) -> str:
    return latest_release(project.game_versions)


@dataclass
class DependencyInfo:
    project_id: str
    dependency_type: str
    project: Project | None


def dependencies_of(version: ProjectVersion | None) -> list[DependencyInfo]:
    """Dependencies of a version with our catalog entries attached (one query)."""
    if version is None:
        return []
    items = [item for item in version.dependencies if item.get("project_id")]
    known = {
        project.external_id: project
        for project in Project.objects.visible().filter(
            external_id__in=[item["project_id"] for item in items]
        )
    }
    return [
        DependencyInfo(
            project_id=item["project_id"],
            dependency_type=item["dependency_type"],
            project=known.get(item["project_id"]),
        )
        for item in items
    ]


def similar(*, project: Project, viewer: Viewer | None = None, limit: int = 8) -> QuerySet[Project]:
    """Same type, sharing categories, most downloaded first."""
    categories = project.categories.all()
    return (
        catalog(viewer)
        .filter(project_type=project.project_type, categories__in=categories)
        .exclude(pk=project.pk)
        .distinct()
        .order_by("-modrinth_downloads")[:limit]
    )
