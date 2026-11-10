"""Our catalog as the compatibility engine's `Index` (tech.md 9.3): reads only, no HTTP."""

from collections.abc import Iterable

from django.db.models import QuerySet

from apps.compat import types as compat

from .models import Project, ProjectVersion

VERSION_FIELDS = (
    "project_id",
    "modrinth_version_id",
    "version_number",
    "version_type",
    "game_versions",
    "loaders",
    "date_published",
    "dependencies",
    "file_url",
    "file_name",
    "file_size",
)


class CatalogIndex:
    """`compat.types.Index` over our catalog: two queries per call, whatever the size.

    Hidden projects are included: a hidden dependency is still needed to run its dependants.
    """

    def __init__(self) -> None:
        self._cache: dict[str, compat.Project] = {}
        self.rows: dict[str, Project] = {}

    def _load(self, queryset: QuerySet[Project]) -> list[compat.Project]:
        every = list(queryset)
        projects = [row for row in every if row.external_id not in self._cache]
        versions: dict[int, list[compat.Version]] = {}
        rows = ProjectVersion.objects.filter(project__in=projects).values_list(*VERSION_FIELDS)
        for row in rows.iterator(chunk_size=2000):
            values = dict(zip(VERSION_FIELDS, row, strict=True))
            versions.setdefault(values["project_id"], []).append(_version(values))
        for row in projects:
            self.rows[row.external_id] = row
            self._cache[row.external_id] = compat.Project(
                id=row.external_id,
                slug=row.slug,
                title=row.title,
                project_type=row.project_type,
                icon_url=row.icon_url,
                versions=tuple(versions.get(row.pk, ())),
            )
        return [self._cache[row.external_id] for row in every]

    def projects(self, ids: Iterable[str]) -> dict[str, compat.Project]:
        ids = set(ids)
        found = {pid: self._cache[pid] for pid in ids if pid in self._cache}
        rest = ids - set(found)
        if rest:
            for project in self._load(Project.objects.filter(external_id__in=rest)):
                found[project.id] = project
        return found

    def by_slug(self, slugs: Iterable[str]) -> dict[str, compat.Project]:
        slugs = set(slugs)
        found = {project.slug: project for project in self._cache.values() if project.slug in slugs}
        rest = slugs - set(found)
        if rest:
            for project in self._load(Project.objects.filter(slug__in=rest)):
                found[project.slug] = project
        return found

    def by_version(self, version_ids: Iterable[str]) -> dict[str, compat.Project]:
        """One query for the owners, one for their versions."""
        wanted = set(version_ids)
        if not wanted:
            return {}
        owners = dict(
            ProjectVersion.objects.filter(modrinth_version_id__in=wanted).values_list(
                "modrinth_version_id", "project_id"
            )
        )
        owner_pks = set(owners.values())
        known = {row.pk for row in self.rows.values()}
        if owner_pks - known:
            self._load(Project.objects.filter(pk__in=owner_pks - known))
        loaded = {
            row.pk: self._cache[external_id]
            for external_id, row in self.rows.items()
            if row.pk in owner_pks
        }
        return {version_id: loaded[pk] for version_id, pk in owners.items() if pk in loaded}

    def hidden(self, slug: str) -> bool:
        return any(row.slug == slug and row.is_hidden for row in self.rows.values())

    def requests(self, projects: Iterable[Project]) -> list[compat.Project]:
        """Catalog rows the caller already holds, as engine projects (one versions query)."""
        rows = list(projects)
        self._load_rows(rows)
        return [self._cache[row.external_id] for row in rows]

    def _load_rows(self, rows: list[Project]) -> None:
        missing = [row.pk for row in rows if row.external_id not in self._cache]
        if missing:
            self._load(Project.objects.filter(pk__in=missing))


def _version(values: dict) -> compat.Version:
    return compat.Version(
        id=values["modrinth_version_id"],
        project_id=str(values["project_id"]),
        version_number=values["version_number"],
        version_type=values["version_type"],
        game_versions=tuple(values["game_versions"]),
        loaders=tuple(values["loaders"]),
        date_published=values["date_published"],
        dependencies=tuple(
            compat.Dependency(
                project_id=item.get("project_id"),
                version_id=item.get("version_id"),
                dependency_type=item.get("dependency_type", "required"),
            )
            for item in values["dependencies"] or []
        ),
        file_url=values["file_url"],
        file_name=values["file_name"],
        file_size=values["file_size"],
    )


def version_of(row: ProjectVersion) -> compat.Version:
    """One stored version as the engine sees it."""
    return _version(
        {name: getattr(row, name) for name in VERSION_FIELDS if name != "project_id"}
        | {"project_id": row.project_id}
    )
