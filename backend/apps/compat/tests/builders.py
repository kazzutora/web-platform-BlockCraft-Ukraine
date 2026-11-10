"""Small in-memory catalogs for engine tests: no database, no HTTP."""

from datetime import UTC, datetime, timedelta

from apps.compat.types import Dependency, Project, Version

_BASE = datetime(2026, 1, 1, tzinfo=UTC)


def version(
    vid: str,
    *,
    game: tuple[str, ...] = ("1.21.1",),
    loaders: tuple[str, ...] = ("fabric",),
    kind: str = "release",
    day: int = 0,
    requires: tuple[str, ...] = (),
    optional: tuple[str, ...] = (),
    forbids: tuple[str, ...] = (),
    pins: dict[str, str] | None = None,
    embedded: tuple[str, ...] = (),
) -> Version:
    pins = pins or {}
    dependencies = (
        *(Dependency(pid, pins.get(pid), "required") for pid in requires),
        *(Dependency(pid, None, "optional") for pid in optional),
        *(Dependency(pid, None, "incompatible") for pid in forbids),
        *(Dependency(pid, None, "embedded") for pid in embedded),
    )
    return Version(
        id=vid,
        project_id="",
        version_number=vid,
        version_type=kind,
        game_versions=game,
        loaders=loaders,
        date_published=_BASE + timedelta(days=day),
        dependencies=dependencies,
        file_url=f"https://cdn.modrinth.com/data/x/{vid}.jar",
        file_name=f"{vid}.jar",
    )


def project(pid: str, *versions: Version, kind: str = "mod", slug: str | None = None) -> Project:
    return Project(
        id=pid, slug=slug or pid.lower(), title=pid, project_type=kind, versions=versions
    )


class MemoryIndex:
    """`Index` over a dict; counts calls so tests can check one load per BFS level."""

    def __init__(self, *projects: Project) -> None:
        self.by_id = {item.id: item for item in projects}
        self.calls = 0

    def projects(self, ids):
        ids = list(ids)
        if ids:
            self.calls += 1
        return {pid: self.by_id[pid] for pid in ids if pid in self.by_id}

    def by_slug(self, slugs):
        slugs = set(slugs)
        return {item.slug: item for item in self.by_id.values() if item.slug in slugs}

    def by_version(self, version_ids):
        wanted = set(version_ids)
        if wanted:
            self.calls += 1
        return {
            version.id: item
            for item in self.by_id.values()
            for version in item.versions
            if version.id in wanted
        }
