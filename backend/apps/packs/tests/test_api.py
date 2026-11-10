import json
import zipfile
from io import BytesIO

import pytest

from apps.accounts.tests.factories import UserFactory
from apps.mods.models import ProjectType
from apps.mods.tests.factories import ProjectFactory, VersionFactory
from apps.packs import tasks
from apps.packs.models import Origin, Pack

from .factories import PackFactory, add, mod

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("game_versions")]


@pytest.fixture(autouse=True)
def no_covers(monkeypatch):
    monkeypatch.setattr(tasks.render_cover, "delay", lambda pack_id: None)


@pytest.fixture(autouse=True)
def offline_modrinth(monkeypatch):
    """Unknown hashes would be asked from Modrinth: tests never go online."""
    from unittest import mock

    from apps.mods.tests.fakes import FakeModrinth

    factory = mock.MagicMock()
    factory.return_value.__enter__.return_value = FakeModrinth()
    monkeypatch.setattr("apps.mods.identify.ModrinthClient", factory)
    return factory


def slugs(response) -> list[str]:
    return [item["slug"] for item in response.json()["results"]]


def test_catalog_lists_only_published_packs_for_everyone(api_client):
    PackFactory(slug="public")
    PackFactory(slug="by-link", visibility="link")
    PackFactory(slug="private", visibility="private")
    PackFactory(slug="draft", status=Pack.Status.DRAFT)

    assert slugs(api_client.get("/api/v1/packs", {"all": "1"})) == ["public"]


def test_catalog_follows_my_game_and_says_whether_a_pack_fits(api_client):
    PackFactory(slug="fabric-26", game_version="26.3", loader="fabric")
    PackFactory(slug="forge-121", game_version="1.21.1", loader="forge")
    api_client.cookies["bc_game"] = "26.3:fabric"

    assert slugs(api_client.get("/api/v1/packs")) == ["fabric-26"]
    cards = api_client.get("/api/v1/packs", {"all": "1"}).json()["results"]
    assert {card["slug"]: card["fits_my_game"] for card in cards} == {
        "fabric-26": True,
        "forge-121": False,
    }


def test_a_link_pack_opens_with_its_token_only(api_client, auth_client, user):
    pack = PackFactory(slug="secret", visibility="link", author=user)

    assert api_client.get("/api/v1/packs/secret").status_code == 404
    assert api_client.get("/api/v1/packs/secret", {"share_token": "nope"}).status_code == 404
    opened = api_client.get("/api/v1/packs/secret", {"share_token": pack.share_token})
    assert opened.status_code == 200
    assert opened.json()["share_token"] is None  # only the author sees it
    assert auth_client.get("/api/v1/packs/secret").json()["share_token"] == pack.share_token


def test_private_and_draft_packs_are_the_authors_only(api_client, auth_client, user):
    PackFactory(slug="mine", visibility="private", author=user)
    PackFactory(slug="theirs", status=Pack.Status.DRAFT)

    assert auth_client.get("/api/v1/packs/mine").status_code == 200
    assert api_client.get("/api/v1/packs/mine").status_code == 404
    assert auth_client.get("/api/v1/packs/theirs").status_code == 404


def test_the_constructor_flow(auth_client):
    api = mod(slug="fabric-api")
    mod(slug="sodium", requires=[api])
    mod(slug="lithium")

    created = auth_client.post(
        "/api/v1/packs",
        {"title": "З другом", "game_version": "26.3", "loader": "fabric"},
        format="json",
    )
    assert created.status_code == 201
    slug = created.json()["slug"]
    for project in ("sodium", "lithium"):
        response = auth_client.post(
            f"/api/v1/packs/{slug}/items", {"project": project}, format="json"
        )
        assert response.status_code == 201

    detail = response.json()
    assert [(item["project"]["slug"], item["reason"]) for item in detail["items"]] == [
        ("sodium", "requested"),
        ("lithium", "requested"),
        ("fabric-api", "dependency"),
    ]
    assert detail["compat"]["status"] == "ok"
    assert detail["compat_status"] == "ok"
    check = auth_client.get(f"/api/v1/packs/{slug}/check").json()
    assert check["status"] == "ok"

    published = auth_client.post(
        f"/api/v1/packs/{slug}/publish", {"visibility": "link"}, format="json"
    )
    assert published.status_code == 200
    assert (published.json()["status"], published.json()["visibility"]) == ("published", "link")


def test_a_pack_with_errors_is_not_published(auth_client, user):
    pack = PackFactory(author=user, status=Pack.Status.DRAFT)
    lights = mod(slug="lights")
    for project in (mod(slug="lamb", breaks=[lights]), lights):
        auth_client.post(f"/api/v1/packs/{pack.slug}/items", {"project": project.slug})

    response = auth_client.post(f"/api/v1/packs/{pack.slug}/publish", {}, format="json")

    assert (response.status_code, response.json()["code"]) == (400, "pack_has_errors")


def test_editing_needs_the_author(api_client, user):
    pack = PackFactory(author=user, status=Pack.Status.DRAFT)
    stranger = UserFactory()
    from rest_framework.test import APIClient

    other = APIClient()
    other.force_login(stranger)
    project = mod(slug="x")

    assert api_client.post(f"/api/v1/packs/{pack.slug}/items", {"project": "x"}).status_code == 401
    # A stranger does not even see the draft
    assert (
        other.post(f"/api/v1/packs/{pack.slug}/items", {"project": project.slug}).status_code == 404
    )


def test_optional_items_and_removal(auth_client, user):
    pack = PackFactory(author=user, status=Pack.Status.DRAFT)
    auth_client.post(f"/api/v1/packs/{pack.slug}/items", {"project": mod(slug="zoom").slug})

    patched = auth_client.patch(
        f"/api/v1/packs/{pack.slug}/items/zoom", {"optional": True}, format="json"
    )
    removed = auth_client.delete(f"/api/v1/packs/{pack.slug}/items/zoom")

    assert patched.json()["items"][0]["env_client"] == "optional"
    assert removed.json()["items"] == []


def test_files_tell_where_each_goes(api_client):
    pack = PackFactory()
    add(pack, mod(slug="sodium"))
    dp = ProjectFactory(slug="terra", project_type=ProjectType.DATAPACK, loaders=["datapack"])
    VersionFactory(project=dp, game_versions=["26.3"], loaders=["datapack"])
    add(pack, dp)

    files = api_client.get(f"/api/v1/packs/{pack.slug}/files").json()

    assert [(f["project"]["slug"], f["folder"]) for f in files] == [
        ("sodium", "mods"),
        ("terra", "datapacks"),
    ]
    assert files[0]["url"].startswith("https://cdn.modrinth.com/")


def test_export_of_a_community_pack_and_of_a_modrinth_one(api_client):
    pack = PackFactory()
    add(pack, mod(slug="sodium"))
    modrinth = PackFactory(
        origin=Origin.MODRINTH,
        source_file_url="https://cdn.modrinth.com/data/F/versions/V/f.mrpack",
    )

    response = api_client.get(f"/api/v1/packs/{pack.slug}/export.mrpack")
    redirect = api_client.get(f"/api/v1/packs/{modrinth.slug}/export.mrpack")

    assert response["Content-Type"] == "application/x-modrinth-modpack+zip"
    with zipfile.ZipFile(BytesIO(response.content)) as archive:
        assert len(json.loads(archive.read("modrinth.index.json"))["files"]) == 1
    assert (redirect.status_code, redirect["Location"]) == (302, modrinth.source_file_url)


def test_retarget_preview_over_http(api_client):
    pack = PackFactory()
    add(pack, mod(slug="both", game_versions=["26.3", "1.21.1"]))
    add(pack, mod(slug="new-only"))

    data = api_client.get(
        f"/api/v1/packs/{pack.slug}/retarget", {"game_version": "1.21.1", "loader": "fabric"}
    ).json()

    assert (data["kept"], data["dropped"]) == (["both"], ["new-only"])
    assert set(data["titles"]) == {"both", "new-only"}


def test_fork_to_another_game(auth_client):
    pack = PackFactory()
    add(pack, mod(slug="both", game_versions=["26.3", "1.21.1"]))

    response = auth_client.post(
        f"/api/v1/packs/{pack.slug}/fork", {"game_version": "1.21.1"}, format="json"
    )

    assert response.status_code == 201
    assert (response.json()["game_version"], response.json()["status"]) == ("1.21.1", "draft")
    assert response.json()["forked_from"]["slug"] == pack.slug


def test_catalog_has_no_n_plus_one(api_client, django_assert_max_num_queries):
    for _ in range(6):
        pack = PackFactory()
        add(pack, mod())

    with django_assert_max_num_queries(5):
        response = api_client.get("/api/v1/packs", {"all": "1"})

    assert len(response.json()["results"]) == 6


def test_save_a_mods_folder_as_a_private_draft(auth_client, user):
    sodium = ProjectFactory(slug="sodium")
    VersionFactory(project=sodium, sha1="a" * 40, game_versions=["26.3"], loaders=["fabric"])
    lithium = ProjectFactory(slug="lithium")
    VersionFactory(project=lithium, sha1="b" * 40, game_versions=["26.3"], loaders=["fabric"])

    response = auth_client.post(
        "/api/v1/packs/import",
        {"files": [{"hash": "a" * 40}, {"hash": "b" * 40}, {"hash": "c" * 40}]},
        format="json",
    )

    assert response.status_code == 201
    data = response.json()
    assert (data["game_version"], data["loader"], data["visibility"]) == (
        "26.3",
        "fabric",
        "private",
    )
    assert {item["project"]["slug"] for item in data["items"]} == {"sodium", "lithium"}
    assert data["status"] == "draft"


def test_save_a_mrpack_index_takes_its_game(auth_client, monkeypatch):
    sodium = ProjectFactory(slug="sodium")
    VersionFactory(project=sodium, sha1="a" * 40, game_versions=["1.21.1"], loaders=["fabric"])
    index = {
        "formatVersion": 1,
        "game": "minecraft",
        "name": "Друзі",
        "files": [{"path": "mods/s.jar", "hashes": {"sha1": "a" * 40}, "downloads": []}],
        "dependencies": {"minecraft": "1.21.1", "fabric-loader": "0.16.0"},
    }

    data = auth_client.post("/api/v1/packs/import", {"index": index}, format="json").json()

    assert (data["title"], data["game_version"], data["loader"]) == ("Друзі", "1.21.1", "fabric")


def test_import_needs_something_and_a_player(api_client, auth_client):
    assert api_client.post("/api/v1/packs/import", {"files": []}, format="json").status_code == 401
    empty = auth_client.post("/api/v1/packs/import", {}, format="json")
    unknown = auth_client.post(
        "/api/v1/packs/import", {"files": [{"hash": "f" * 40}]}, format="json"
    )

    assert empty.status_code == 400
    assert (unknown.status_code, unknown.json()["code"]) == (400, "unknown_target")


def test_a_broken_index_is_a_field_error(auth_client):
    response = auth_client.post("/api/v1/packs/import", {"index": {"files": 3}}, format="json")

    assert (response.status_code, response.json()["code"]) == (400, "invalid_mrpack")


def test_hidden_projects_are_not_picked_on_import(auth_client):
    shown = ProjectFactory(slug="shown")
    VersionFactory(project=shown, sha1="a" * 40, game_versions=["26.3"], loaders=["fabric"])
    hidden = ProjectFactory(slug="hidden", is_hidden=True)
    VersionFactory(project=hidden, sha1="b" * 40, game_versions=["26.3"], loaders=["fabric"])

    data = auth_client.post(
        "/api/v1/packs/import",
        {
            "files": [{"hash": "a" * 40}, {"hash": "b" * 40}],
            "game_version": "26.3",
            "loader": "fabric",
        },
        format="json",
    ).json()

    assert [item["project"]["slug"] for item in data["items"]] == ["shown"]
