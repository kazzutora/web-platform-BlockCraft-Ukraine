"""/import: files known by their SHA-1 (recorded `/version_files` answers)."""

from contextlib import contextmanager
from unittest import mock

import pytest

from apps.compat.types import Target
from apps.mods import identify
from apps.mods.models import Project
from apps.sources.clients.modrinth import ModrinthError
from apps.sources.tests.recorded import load

from .factories import ProjectFactory, VersionFactory
from .fakes import FakeModrinth

pytestmark = pytest.mark.django_db

SODIUM_SHA1 = "2172d0e9a5fbdd6791c27769867334382ba6be02"


class HashModrinth(FakeModrinth):
    """Answers /version_files and /version_files/update with the recorded bodies."""

    def __init__(self):
        super().__init__([load("modrinth", "project_sodium")])
        self.asked: list[list[str]] = []

    def versions_by_hashes(self, hashes, *, algorithm="sha1"):
        from apps.sources.schemas.modrinth import ModrinthVersion

        self.asked.append(list(hashes))
        recorded = load("modrinth", "version_files_sha1")
        return {h: ModrinthVersion.model_validate(v) for h, v in recorded.items() if h in hashes}

    def latest_by_hashes(self, hashes, *, loaders, game_versions, algorithm="sha1"):
        from apps.sources.schemas.modrinth import ModrinthVersion

        self.asked.append(["update", *hashes])
        recorded = load("modrinth", "version_files_update")
        return {h: ModrinthVersion.model_validate(v) for h, v in recorded.items() if h in hashes}


@contextmanager
def modrinth(fake):
    with mock.patch("apps.mods.identify.ModrinthClient") as factory:
        factory.return_value.__enter__.return_value = fake
        yield


def test_unknown_hashes_are_learned_from_modrinth_once():
    fake = HashModrinth()

    with modrinth(fake):
        first = identify.identify([SODIUM_SHA1, "0" * 40])
        again = identify.identify([SODIUM_SHA1.upper(), "0" * 40])

    assert first.known[SODIUM_SHA1].project.slug == "sodium"
    assert first.unknown == ["0" * 40]
    assert Project.objects.get(slug="sodium").external_id == "AANobbMI"
    assert fake.asked == [
        [SODIUM_SHA1, "0" * 40]
    ]  # the second ask came from the database and cache
    assert again.unknown == ["0" * 40]


def test_known_files_guess_the_game():
    for n in range(3):
        project = ProjectFactory()
        VersionFactory(
            project=project, sha1=f"{n}" * 40, game_versions=["1.21.1"], loaders=["fabric"]
        )

    found = identify.identify(f"{n}" * 40 for n in range(3))

    assert found.guess.target == Target("1.21.1", "fabric")
    assert (found.guess.fitting, found.guess.identified) == (3, 3)


def test_a_silent_modrinth_is_reported_not_raised():
    fake = HashModrinth()
    fake.versions_by_hashes = mock.Mock(side_effect=ModrinthError("down"))

    with modrinth(fake):
        found = identify.identify(["1" * 40])

    assert found.source_unavailable
    assert found.unknown == ["1" * 40]


def test_updates_name_the_newest_file_for_the_target():
    fake = HashModrinth()
    with modrinth(fake):
        found = identify.identify([SODIUM_SHA1])
        rows, unavailable = identify.updates(found.known, Target("1.21.4", "fabric"))
        identify.updates(found.known, Target("1.21.4", "fabric"))

    assert not unavailable
    assert rows[0].latest.version_number == "mc1.21.4-0.6.13-fabric"
    assert sum(1 for call in fake.asked if call[0] == "update") == 1  # cached the second time


def test_identify_and_updates_over_http(api_client):
    fake = HashModrinth()
    files = [{"hash": SODIUM_SHA1, "name": "sodium.jar"}, {"hash": "0" * 40, "name": "x.jar"}]

    with modrinth(fake):
        known = api_client.post("/api/v1/compat/identify", {"files": files}, format="json").json()
        update = api_client.post(
            "/api/v1/compat/updates",
            {"files": files, "game_version": "1.21.4", "loader": "fabric"},
            format="json",
        ).json()

    assert [(item["name"], item["project"]["slug"]) for item in known["known"]] == [
        ("sodium.jar", "sodium")
    ]
    assert known["unknown"] == [{"hash": "0" * 40, "name": "x.jar"}]
    assert update["files"][0]["status"] in {"update", "up_to_date"}
    assert update["target"] == {"game_version": "1.21.4", "loader": "fabric"}


def test_identify_refuses_what_is_not_a_hash(api_client):
    response = api_client.post(
        "/api/v1/compat/identify", {"files": [{"hash": "nope"}]}, format="json"
    )

    assert response.status_code == 400
