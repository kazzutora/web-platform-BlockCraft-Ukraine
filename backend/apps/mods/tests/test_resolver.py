from datetime import UTC, datetime

import pytest

from apps.mods import selectors
from apps.mods.models import ProjectType, ProjectVersion

from .factories import ProjectFactory, VersionFactory

pytestmark = pytest.mark.django_db


def at(day: int) -> datetime:
    return datetime(2026, 10, day, tzinfo=UTC)


def test_newest_release_wins_over_newer_beta():
    project = ProjectFactory()
    release = VersionFactory(project=project, released_at=at(1))
    VersionFactory(project=project, released_at=at(5), version_type=ProjectVersion.VersionType.BETA)
    VersionFactory(project=project, released_at=at(2), game_versions=["1.21.1"])

    assert (
        selectors.resolve_version(project=project, game_version="26.3", loader="fabric") == release
    )


def test_beta_is_used_when_there_is_no_release():
    project = ProjectFactory()
    beta = VersionFactory(project=project, version_type=ProjectVersion.VersionType.BETA)

    assert selectors.resolve_version(project=project, game_version="26.3", loader="fabric") == beta


def test_loader_must_match_for_mods():
    project = ProjectFactory(loaders=["fabric", "neoforge"])
    VersionFactory(project=project, loaders=["fabric"], released_at=at(9))
    neoforge = VersionFactory(project=project, loaders=["neoforge"], released_at=at(1))

    assert (
        selectors.resolve_version(project=project, game_version="26.3", loader="neoforge")
        == neoforge
    )
    assert selectors.resolve_version(project=project, game_version="26.3", loader="forge") is None


@pytest.mark.parametrize("project_type", [ProjectType.SHADER, ProjectType.RESOURCEPACK])
def test_loader_is_ignored_for_shaders_and_resource_packs(project_type):
    project = ProjectFactory(project_type=project_type, loaders=["iris", "optifine"])
    version = VersionFactory(project=project, loaders=["iris"])

    assert (
        selectors.resolve_version(project=project, game_version="26.3", loader="fabric") == version
    )


def test_nearest_versions_for_the_same_loader():
    project = ProjectFactory()
    VersionFactory(project=project, game_versions=["1.21.1", "1.21.4"], loaders=["fabric"])
    VersionFactory(project=project, game_versions=["1.20.1"], loaders=["fabric"])
    VersionFactory(project=project, game_versions=["1.21.3"], loaders=["forge"])
    VersionFactory(project=project, game_versions=["24w14a"], loaders=["fabric"])

    assert selectors.nearest_game_versions(
        project=project, game_version="1.21.3", loader="fabric"
    ) == ["1.21.4", "1.21.1", "1.20.1"]
