"""A stand-in for ModrinthClient that answers with recorded or given payloads."""

from apps.sources.clients.modrinth import ModrinthNotFoundError
from apps.sources.schemas.modrinth import (
    ModrinthCategory,
    ModrinthProject,
    ModrinthVersion,
    SearchHit,
    SearchResponse,
)
from apps.sources.tests.recorded import load


class FakeModrinth:
    """Behaves like the real API where it matters: `/projects` skips unknown ids."""

    def __init__(
        self, projects: list[dict] | None = None, versions: dict[str, list[dict]] | None = None
    ):
        self.projects = {item["id"]: item for item in projects or []}
        self.versions = versions or {}
        self.version_calls: list[tuple[str, list[str]]] = []
        #: Search hits per project type; defaults to the projects of that Modrinth type
        self.hits: dict[str, list[str]] = {}

    def get_categories(self):
        return [ModrinthCategory.model_validate(item) for item in load("modrinth", "tag_category")]

    def search(self, *, project_type, game_versions=(), offset=0, limit=100):
        ids = self.hits.get(project_type) or [
            item["id"] for item in self.projects.values() if item["project_type"] == project_type
        ]
        hits = [
            SearchHit(
                project_id=pid,
                slug=self.projects[pid]["slug"],
                project_type=self.projects[pid]["project_type"],
                title=self.projects[pid]["title"],
            )
            for pid in ids
        ]
        return SearchResponse(
            hits=hits[offset : offset + limit], offset=offset, limit=limit, total_hits=len(hits)
        )

    def get_projects(self, ids):
        return [ModrinthProject.model_validate(self.projects[i]) for i in ids if i in self.projects]

    def get_project(self, id_or_slug):
        for item in self.projects.values():
            if id_or_slug in (item["id"], item["slug"]):
                return ModrinthProject.model_validate(item)
        raise ModrinthNotFoundError(id_or_slug)

    def get_versions(self, project_id, *, game_versions=(), loaders=()):
        self.version_calls.append((project_id, list(game_versions)))
        return [ModrinthVersion.model_validate(item) for item in self.versions.get(project_id, [])]


def recorded() -> FakeModrinth:
    """Sodium, Sodium Extra's versions, a datapack, Terralith and a modpack — all recorded."""
    projects = [
        load("modrinth", "project_sodium"),
        load("modrinth", "project_datapack"),
        load("modrinth", "project_terralith"),
        load("modrinth", "project_modpack"),
    ]
    versions = {
        "AANobbMI": load("modrinth", "project_versions_sodium"),
        "TiFXQSAQ": load("modrinth", "project_versions_datapack"),
        "8oi3bsk5": load("modrinth", "project_versions_terralith"),
    }
    return FakeModrinth(projects, versions)
