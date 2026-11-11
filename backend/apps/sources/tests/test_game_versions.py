import pytest
import respx

from apps.sources import selectors, services, tasks
from apps.sources.clients.modrinth import BASE_URL, ModrinthClient
from apps.sources.models import GameVersion, SyncRun
from apps.sources.runs import SyncCounter

from .recorded import load

pytestmark = pytest.mark.django_db


def sync() -> SyncCounter:
    run = SyncCounter()
    with respx.mock:
        respx.get(f"{BASE_URL}/tag/game_version").respond(json=load("modrinth", "tag_game_version"))
        with ModrinthClient(sleep=lambda seconds: None) as client:
            services.sync_game_versions(client=client, run=run)
    return run


@pytest.mark.parametrize(
    ("version", "version_type", "expected"),
    [
        ("26.3", "release", True),
        ("1.21.1", "release", True),
        ("1.16", "release", True),
        ("1.15.2", "release", False),
        ("1.12.2", "release", True),  # SUPPORTED_LEGACY_VERSIONS
        ("1.8.9", "release", True),
        ("26.4-snapshot-7", "snapshot", False),
        ("1.21.11-rc1", "release", False),
        ("b1.7.3", "beta", False),
    ],
)
def test_supported_versions_are_releases_from_1_16_and_legacy(version, version_type, expected):
    assert services.is_supported(version, version_type) is expected


def test_legacy_versions_come_from_settings(settings):
    settings.SUPPORTED_LEGACY_VERSIONS = ["1.7.10"]

    assert services.is_supported("1.7.10", "release")
    assert not services.is_supported("1.12.2", "release")


def test_sync_stores_every_version_and_marks_the_supported_ones():
    run = sync()

    assert (run.created, run.updated, run.skipped) == (922, 0, 0)
    supported = services.supported_game_versions()
    assert len(supported) == 42
    assert supported[:3] == ["26.3", "26.2", "26.1.2"]
    assert supported[-3:] == ["1.16", "1.12.2", "1.8.9"]
    latest = GameVersion.objects.get(pk="26.3")
    assert (latest.version_type, latest.is_major) == ("release", True)
    assert latest.released_at is not None


def test_sync_is_idempotent_and_counts_changes(settings):
    sync()
    assert sync().unchanged == 922

    settings.SUPPORTED_LEGACY_VERSIONS = []
    run = sync()

    assert run.updated == 2
    assert not GameVersion.objects.get(pk="1.12.2").is_supported


def test_a_version_kept_from_a_profile_gets_filled_in():
    GameVersion.objects.create(version="1.21.1", version_type="release", is_supported=True)

    run = sync()

    assert run.updated == 1
    assert GameVersion.objects.get(pk="1.21.1").released_at is not None


def test_a_version_modrinth_no_longer_lists_stops_being_supported():
    GameVersion.objects.create(version="1.21.99", version_type="release", is_supported=True)

    run = sync()

    assert not GameVersion.objects.get(pk="1.21.99").is_supported
    assert "1.21.99" not in services.supported_game_versions()
    assert run.updated == 1


def test_sync_takes_a_fixed_number_of_queries(django_assert_max_num_queries):
    with django_assert_max_num_queries(8):
        sync()


def test_catalog_syncs_refuse_to_run_without_versions():
    with pytest.raises(services.NoGameVersionsError, match="j=game_versions"):
        services.supported_game_versions()


def test_task_writes_a_sync_run_and_refreshes_meta(api_client):
    assert api_client.get("/api/v1/meta").json()["game_versions"] == []  # cached while empty
    with respx.mock:
        respx.get(f"{BASE_URL}/tag/game_version").respond(json=load("modrinth", "tag_game_version"))
        result = tasks.sync_game_versions.delay().get()

    assert result["created"] == 922
    assert SyncRun.objects.get(job="modrinth.game_versions").status == SyncRun.Status.OK
    assert len(api_client.get("/api/v1/meta").json()["game_versions"]) == 42


def test_meta_lists_supported_versions_loaders_and_categories(api_client, game_versions):
    from apps.mods.models import Category

    Category.objects.create(slug="optimization", name_uk="Оптимізація", project_type="mod")

    body = api_client.get("/api/v1/meta").json()

    assert [item["version"] for item in body["game_versions"]] == game_versions
    assert set(body["game_versions"][0]) == {"version", "version_type", "released_at", "is_major"}
    assert body["loaders"] == ["fabric", "forge", "neoforge", "quilt", "vanilla"]
    assert body["categories"] == [
        {"slug": "optimization", "name": "Оптимізація", "project_type": "mod", "header": ""}
    ]


def test_meta_is_cached(api_client, game_versions, django_assert_num_queries):
    api_client.get("/api/v1/meta")

    with django_assert_num_queries(0):
        assert api_client.get("/api/v1/meta").status_code == 200

    selectors.forget_meta()
    with django_assert_num_queries(4):
        api_client.get("/api/v1/meta")


def test_profile_takes_only_supported_versions(auth_client, user, game_versions):
    GameVersion.objects.create(version="26.4-snapshot-7", version_type="snapshot")
    url = "/api/v1/me/game"

    assert auth_client.patch(url, {"game_version": "26.4-snapshot-7"}).status_code == 400
    assert auth_client.patch(url, {"game_version": "1.21.1"}).json()["game_version"] == "1.21.1"
    assert auth_client.patch(url, {"game_version": ""}).json()["game_version"] is None
    user.game_profile.refresh_from_db()
    assert user.game_profile.game_version is None
