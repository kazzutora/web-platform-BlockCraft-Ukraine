import pytest

from apps.mods import services
from apps.mods.clients import ModrinthNotFoundError
from apps.mods.models import Category, Project, ProjectVersion
from apps.mods.schemas import (
    ModrinthCategory,
    ModrinthProject,
    ModrinthVersion,
    SearchHit,
    SearchResponse,
)

from .payloads import CATEGORIES, project_payload, version_payload

pytestmark = pytest.mark.django_db


class FakeModrinth:
    """Stands in for ModrinthClient with canned data."""

    def __init__(self, projects: list[dict], versions: dict[str, list[dict]]):
        self.projects = {item["id"]: item for item in projects}
        self.versions = versions
        self.version_calls: list[tuple[str, list[str]]] = []

    def get_categories(self):
        return [ModrinthCategory.model_validate(item) for item in CATEGORIES]

    def search(self, *, project_type, game_versions=(), offset=0, limit=100):
        hits = [
            SearchHit(
                project_id=p["id"], slug=p["slug"], project_type=p["project_type"], title=p["title"]
            )
            for p in self.projects.values()
            if p["project_type"] == project_type
        ]
        page = hits[offset : offset + limit]
        return SearchResponse(hits=page, offset=offset, limit=limit, total_hits=len(hits))

    def get_projects(self, ids):
        return [ModrinthProject.model_validate(self.projects[i]) for i in ids]

    def get_project(self, slug):
        for item in self.projects.values():
            if item["slug"] == slug:
                return ModrinthProject.model_validate(item)
        raise ModrinthNotFoundError(slug)

    def get_versions(self, project_id, *, game_versions=(), loaders=()):
        self.version_calls.append((project_id, list(game_versions)))
        return [ModrinthVersion.model_validate(item) for item in self.versions.get(project_id, [])]


@pytest.fixture
def fake():
    return FakeModrinth(
        projects=[
            project_payload(),
            project_payload("IRIS0001", "iris"),
            project_payload(
                "HVnmMxH1",
                "complementary",
                "shader",
                categories=["low", "high"],
                loaders=["iris", "optifine"],
            ),
        ],
        versions={
            "AANobbMI": [
                version_payload("v1", game_versions=["26.3"]),
                version_payload("v2", game_versions=["1.21.1"], version_type="beta"),
            ],
            "IRIS0001": [
                version_payload(
                    "i1",
                    project_id="IRIS0001",
                    dependencies=[{"project_id": "AANobbMI", "dependency_type": "required"}],
                )
            ],
        },
    )


def sync(fake, limits=None):
    return services.sync_popular(
        client=fake,
        limits=limits or {"mod": 300, "resourcepack": 100, "shader": 100},
        game_versions=["26.3", "1.21.1"],
        progress=lambda message: None,
    )


def test_sync_creates_categories_projects_and_versions(fake):
    result = sync(fake)

    assert result.projects == {"mod": 2, "resourcepack": 0, "shader": 1}
    assert result.versions == 3
    assert Category.objects.count() == 3  # plugin categories are skipped
    sodium = Project.objects.get(slug="sodium")
    assert sodium.status == Project.Status.PUBLISHED
    assert sodium.categories.get().name_uk == "Оптимізація"
    assert sodium.gallery[0]["url"].endswith("b.webp")  # featured image first
    assert sodium.license == "MIT License"
    assert sodium.versions.count() == 2
    assert fake.version_calls[0] == ("AANobbMI", ["26.3", "1.21.1"])


def test_sync_is_idempotent(fake):
    sync(fake)
    counts = (Project.objects.count(), ProjectVersion.objects.count(), Category.objects.count())

    sync(fake)

    assert counts == (
        Project.objects.count(),
        ProjectVersion.objects.count(),
        Category.objects.count(),
    )


def test_sync_respects_limits(fake):
    result = sync(fake, limits={"mod": 1})

    assert result.projects == {"mod": 1}
    assert Project.objects.count() == 1


def test_sync_keeps_moderation_status_and_manual_gpu_load(fake):
    sync(fake)
    Project.objects.filter(slug="sodium").update(status=Project.Status.HIDDEN)
    Project.objects.filter(slug="complementary").update(gpu_load="heavy", gpu_load_manual=True)

    sync(fake)

    assert Project.objects.get(slug="sodium").status == Project.Status.HIDDEN
    assert Project.objects.get(slug="complementary").gpu_load == "heavy"


def test_shader_gpu_load_comes_from_performance_categories(fake):
    sync(fake)

    assert Project.objects.get(slug="complementary").gpu_load == "light"


def test_versions_missing_upstream_are_removed(fake):
    sync(fake)
    fake.versions["AANobbMI"] = fake.versions["AANobbMI"][:1]

    sync(fake)

    assert list(
        Project.objects.get(slug="sodium").versions.values_list("modrinth_version_id", flat=True)
    ) == ["v1"]


def test_description_is_rendered_without_scripts(fake):
    sync(fake)

    html = Project.objects.get(slug="sodium").body_html
    assert "<h1>Hello</h1>" in html
    assert "<script" not in html


def test_suggested_project_waits_for_moderation(fake, user):
    project = services.import_suggested(
        client=fake, slug="iris", suggested_by=user, game_versions=["26.3"]
    )

    assert project.status == Project.Status.PENDING
    assert project.suggested_by == user
    assert project.published_at is None
    assert project.versions.count() == 1

    services.publish(project=project)
    project.refresh_from_db()
    assert project.status == Project.Status.PUBLISHED
    assert project.published_at is not None


def test_suggesting_a_known_project_changes_nothing(fake, user):
    sync(fake)

    project = services.import_suggested(
        client=fake, slug="sodium", suggested_by=user, game_versions=["26.3"]
    )

    assert project.status == Project.Status.PUBLISHED
    assert project.suggested_by is None


def test_unsupported_project_type_is_rejected(fake, user):
    fake.projects["PLUGIN01"] = project_payload("PLUGIN01", "essentials", "plugin")

    with pytest.raises(services.DomainError):
        services.import_suggested(
            client=fake, slug="essentials", suggested_by=user, game_versions=["26.3"]
        )
