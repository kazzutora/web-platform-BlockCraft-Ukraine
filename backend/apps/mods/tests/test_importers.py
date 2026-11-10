"""Importers on recorded Modrinth answers (apps/sources/tests/fixtures/modrinth/)."""

import pytest

from apps.core.exceptions import DomainError
from apps.core.models import Source
from apps.mods import importers
from apps.mods.categories import CATEGORY_NAMES_UK
from apps.mods.importers import Outcome
from apps.mods.models import Category, Project, ProjectType, Side
from apps.sources.schemas.modrinth import ModrinthCategory, ModrinthProject, ModrinthVersion
from apps.sources.tests.recorded import load

pytestmark = pytest.mark.django_db


def project(name: str, **changes) -> ModrinthProject:
    return ModrinthProject.model_validate({**load("modrinth", name), **changes})


def versions(name: str) -> list[ModrinthVersion]:
    return [ModrinthVersion.model_validate(item) for item in load("modrinth", name)]


@pytest.fixture
def categories():
    importers.upsert_categories(
        ModrinthCategory.model_validate(item) for item in load("modrinth", "tag_category")
    )


def test_new_project_is_created_with_source_fields(categories):
    sodium, outcome = importers.import_project(project("project_sodium"))

    assert outcome == Outcome.CREATED
    assert (sodium.source, sodium.external_id) == (Source.MODRINTH, "AANobbMI")
    assert sodium.external_url == "https://modrinth.com/mod/sodium"
    assert sodium.project_type == ProjectType.MOD
    assert (sodium.client_side, sodium.server_side) == (Side.REQUIRED, Side.UNSUPPORTED)
    assert sodium.modrinth_follows == 42576
    assert sodium.categories.get().name_uk == "Оптимізація"
    assert sodium.gallery and sodium.body_html
    assert sodium.synced_at is not None
    assert not sodium.is_hidden


def test_same_page_is_unchanged_but_counters_move():
    importers.import_project(project("project_sodium"))

    again, outcome = importers.import_project(project("project_sodium", downloads=1, followers=2))

    assert outcome == Outcome.UNCHANGED
    again.refresh_from_db()
    assert (again.modrinth_downloads, again.modrinth_follows) == (1, 2)
    assert Project.objects.count() == 1


def test_changed_page_is_updated():
    importers.import_project(project("project_sodium"))

    sodium, outcome = importers.import_project(
        project("project_sodium", title="Sodium 2", updated="2026-11-08T00:00:00Z")
    )

    assert outcome == Outcome.UPDATED
    assert Project.objects.get().title == "Sodium 2" == sodium.title


def test_hidden_project_stays_hidden_after_sync():
    sodium, _ = importers.import_project(project("project_sodium"))
    Project.objects.filter(pk=sodium.pk).update(is_hidden=True, hidden_reason="spam")

    importers.import_project(project("project_sodium", updated="2026-11-08T00:00:00Z"))

    sodium.refresh_from_db()
    assert sodium.is_hidden and sodium.hidden_reason == "spam"


def test_imported_by_is_set_only_on_creation(user):
    importers.import_project(project("project_sodium"), imported_by=user)
    importers.import_project(project("project_sodium", updated="2026-11-08T00:00:00Z"))

    assert Project.objects.get().imported_by == user


def test_datapack_only_project_becomes_a_datapack(categories):
    pack, _ = importers.import_project(project("project_datapack"))

    assert pack.project_type == ProjectType.DATAPACK
    assert pack.external_url == "https://modrinth.com/datapack/mysticmons"
    # Modrinth tags datapacks with mod categories; we keep copies for the datapack tab
    assert set(pack.categories.values_list("slug", "project_type")) == {
        ("mobs", "datapack"),
        ("game-mechanics", "datapack"),
        ("utility", "datapack"),
    }


def test_mod_that_also_ships_a_datapack_stays_a_mod():
    terralith, _ = importers.import_project(project("project_terralith"))

    assert terralith.project_type == ProjectType.MOD
    assert "datapack" in terralith.loaders


def test_modpack_is_not_a_catalog_project():
    with pytest.raises(DomainError) as error:
        importers.import_project(project("project_modpack"))

    assert error.value.code == "unsupported_type"
    assert importers.project_type_of(project("project_modpack")) is None


def test_shader_gpu_load_comes_from_performance_categories():
    data = project("project_sodium", project_type="shader", categories=["low", "high"])

    shader, _ = importers.import_project(data)

    assert shader.gpu_load == "light"


def test_versions_keep_hashes_and_dependencies_with_version_id():
    extra, _ = importers.import_project(
        project("project_sodium", id="PtjYWJkn", slug="sodium-extra")
    )

    count = importers.import_versions(extra, versions("project_versions_sodium_extra"))

    assert count == 2
    version = extra.versions.get(modrinth_version_id="CmiqMBZT")
    assert len(version.sha1) == 40 and len(version.sha512) == 128
    assert {"project_id": "AANobbMI", "version_id": None, "dependency_type": "required"} in (
        version.dependencies
    )
    assert all(
        set(item) == {"project_id", "version_id", "dependency_type"}
        for item in version.dependencies
    )
    assert extra.versions_synced_at is not None


def test_versions_are_mirrored_idempotently(django_assert_max_num_queries):
    sodium, _ = importers.import_project(project("project_sodium"))
    recorded = versions("project_versions_sodium")
    importers.import_versions(sodium, recorded)

    with django_assert_max_num_queries(6):
        importers.import_versions(sodium, recorded)
    importers.import_versions(sodium, recorded[:1])

    assert list(sodium.versions.values_list("modrinth_version_id", flat=True)) == ["SMxNOGZ6"]


def test_datapack_files_of_a_mod_are_kept_with_their_loader():
    terralith, _ = importers.import_project(project("project_terralith"))

    importers.import_versions(terralith, versions("project_versions_terralith"))

    assert terralith.versions.filter(loaders__contains=["datapack"]).count() == 1


def test_categories_cover_every_type_with_ukrainian_names(categories):
    recorded = {
        item["name"]
        for item in load("modrinth", "tag_category")
        if item["project_type"] in ProjectType.values
    }

    assert recorded <= set(CATEGORY_NAMES_UK)
    assert Category.objects.filter(project_type=ProjectType.DATAPACK).count() == (
        Category.objects.filter(project_type=ProjectType.MOD).count()
    )
