import json
import zipfile
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.tests.factories import UserFactory
from apps.moderation.models import BannedWord
from apps.packs import tasks
from apps.packs.models import Pack, PackItem
from apps.social.models import Review

from .factories import PackFactory, add, mod

pytestmark = pytest.mark.django_db

FORM = {
    "title": "Затишна Січ",
    "summary": "Виживання з оптимізацією",
    "game_version": "26.3",
    "loader": "fabric",
    "style_tags": ["performance", "survival"],
    "ram_min_gb": 6,
    "install_md": "1. Імпортуй у **Prism Launcher**",
}


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_login(user)
    return client


@pytest.fixture(autouse=True)
def _no_background(monkeypatch):
    monkeypatch.setattr(tasks.fill_dependencies, "delay", lambda pack_id: None)


@pytest.fixture
def draft(user):
    return PackFactory(author=user, status=Pack.Status.DRAFT, published_at=None)


# Catalog


def test_catalog_lists_published_packs_with_icons(api_client):
    pack = PackFactory(title="Оптимізація")
    sodium = mod(slug="sodium", icon_url="https://cdn.modrinth.com/sodium.webp")
    add(pack, mod(slug="fabric-api"), added_as_dependency=True)
    add(pack, sodium)
    PackFactory(status=Pack.Status.DRAFT)
    PackFactory(status=Pack.Status.PENDING)

    body = api_client.get("/api/v1/packs").json()

    assert [row["slug"] for row in body["results"]] == [pack.slug]
    row = body["results"][0]
    assert row["mods_count"] == 2
    # Mods the author picked come before dependencies
    assert [icon["slug"] for icon in row["icons"]] == ["sodium", "fabric-api"]
    assert row["icons"][0]["icon_url"] == "https://cdn.modrinth.com/sodium.webp"
    assert row["is_favorited"] is False


def test_catalog_filters(api_client):
    fabric = PackFactory(slug="fabric", style_tags=["tech"], title="Техно")
    PackFactory(slug="forge", loader="forge", game_version="1.20.1", style_tags=["magic"])
    PackFactory(slug="official", is_official=True, modrinth_id="FABULOUS", title="Офіційна")

    def slugs(**params) -> set[str]:
        return {row["slug"] for row in api_client.get("/api/v1/packs", params).json()["results"]}

    assert slugs(loader="forge") == {"forge"}
    assert slugs(game_version="1.20.1") == {"forge"}
    assert slugs(style="tech,quests") == {"fabric"}
    assert slugs(official="true") == {"official"}
    assert slugs(q="техно") == {"fabric"}
    assert slugs(author=fabric.author.nickname.upper()) == {"fabric"}
    assert slugs(sort="new") == {"fabric", "forge", "official"}


def test_catalog_has_no_n_plus_one(auth_client, django_assert_max_num_queries):
    for _ in range(6):
        pack = PackFactory()
        for _ in range(3):
            add(pack, mod())

    with django_assert_max_num_queries(5):
        response = auth_client.get("/api/v1/packs")

    assert len(response.json()["results"]) == 6


def test_my_packs_include_drafts(auth_client, draft):
    PackFactory()

    body = auth_client.get("/api/v1/me/packs").json()

    assert [(row["slug"], row["status"]) for row in body["results"]] == [(draft.slug, "draft")]


# Page


def test_pack_page_shows_files_issues_and_requirements(api_client):
    pack = PackFactory(ram_min_gb=6, loader_version="")
    sodium = add(pack, mod(slug="sodium", unknown=["FLYWHEEL"]))
    add(pack, mod(slug="faithful", project_type="resourcepack"), is_required=False)

    response = api_client.get(f"/api/v1/packs/{pack.slug}")

    assert response.status_code == 200
    body = response.json()
    assert [item["project"]["slug"] for item in body["items"]] == ["sodium", "faithful"]
    assert body["items"][0]["version"]["file_name"] == sodium.version.file_name
    assert body["items"][1]["is_required"] is False
    assert body["total_size"] == 2048
    assert body["effective_loader_version"] == ""
    assert body["issues"] == [
        {
            "type": "missing_dependency",
            "project": {"slug": "sodium", "title": sodium.project.title, "icon_url": ""},
            "other": None,
            "other_modrinth_id": "FLYWHEEL",
            "message": "Потрібна залежність, якої поки немає в нашому каталозі.",
        }
    ]
    assert body["is_mine"] is False
    assert body["modrinth_url"] is None


def test_drafts_are_seen_only_by_their_author(api_client, draft, user):
    assert api_client.get(f"/api/v1/packs/{draft.slug}").status_code == 404
    assert client_for(UserFactory()).get(f"/api/v1/packs/{draft.slug}").status_code == 404

    body = client_for(user).get(f"/api/v1/packs/{draft.slug}").json()

    assert body["is_mine"] is True
    assert body["status"] == "draft"


# Constructor


def test_guests_cannot_create(api_client):
    assert api_client.post("/api/v1/packs", FORM, format="json").status_code in (401, 403)


def test_constructor_flow(auth_client, user):
    api = mod(slug="fabric-api")
    mod(slug="sodium", requires=[api])
    mod(slug="lithium")

    response = auth_client.post("/api/v1/packs", FORM, format="json")
    assert response.status_code == 201, response.json()
    created = response.json()
    assert (created["slug"], created["status"]) == ("zatyshna-sich", "draft")
    assert "<strong>Prism Launcher</strong>" in created["install_html"]
    url = f"/api/v1/packs/{created['slug']}"

    body = auth_client.post(f"{url}/items", {"project": "sodium"}, format="json").json()
    assert {(i["project"]["slug"], i["added_as_dependency"]) for i in body["items"]} == {
        ("sodium", False),
        ("fabric-api", True),
    }
    body = auth_client.patch(f"{url}/items/fabric-api", {"is_required": False}, format="json")
    assert body.json()["items"][1]["is_required"] is False

    response = auth_client.post(f"{url}/publish")
    assert response.status_code == 400
    assert response.json()["code"] == "too_few"

    auth_client.post(f"{url}/items", {"project": "lithium"}, format="json")
    body = auth_client.delete(f"{url}/items/sodium").json()
    assert [i["project"]["slug"] for i in body["items"]] == ["lithium"]
    auth_client.post(f"{url}/items", {"project": "sodium"}, format="json")

    body = auth_client.post(f"{url}/publish").json()
    assert body["status"] == "published"


def test_add_item_errors(auth_client, draft):
    old = mod(slug="old", title="Old", game_versions=["1.20.1"])
    url = f"/api/v1/packs/{draft.slug}/items"

    response = auth_client.post(url, {"project": "old"}, format="json")
    assert response.status_code == 400
    assert response.json()["fields"] == {
        "project": [f"У «{old.title}» немає файлу для 26.3 · Fabric."]
    }

    assert auth_client.post(url, {"project": "missing"}, format="json").status_code == 404
    assert auth_client.delete(f"{url}/missing").status_code == 404


def test_strangers_cannot_change_a_pack(draft):
    mod(slug="sodium")
    stranger = client_for(UserFactory())
    pack = PackFactory()

    assert (
        stranger.post(f"/api/v1/packs/{pack.slug}/items", {"project": "sodium"}).status_code == 403
    )
    assert stranger.patch(f"/api/v1/packs/{pack.slug}", {"title": "Моя"}).status_code == 403
    assert stranger.delete(f"/api/v1/packs/{pack.slug}").status_code == 403
    # Someone else's draft does not even exist for them
    assert stranger.post(f"/api/v1/packs/{draft.slug}/publish").status_code == 404


def test_edit_retargets_and_validates(auth_client, draft):
    url = f"/api/v1/packs/{draft.slug}"

    body = auth_client.patch(url, {"loader": "neoforge", "loader_version": "21.1.200"}).json()
    assert (body["loader"], body["effective_loader_version"]) == ("neoforge", "21.1.200")

    response = auth_client.patch(url, {"loader": "vanilla"}, format="json")
    assert response.status_code == 400
    response = auth_client.patch(url, {"loader_version": "1.0; rm"}, format="json")
    assert response.json()["fields"] == {"loader_version": ["Лише цифри, літери, крапки й дефіси."]}


def test_banned_words_are_refused(auth_client):
    BannedWord.objects.create(word="кринж")

    response = auth_client.post("/api/v1/packs", {**FORM, "summary": "Повний кринж"}, format="json")

    assert response.status_code == 400
    assert response.json()["code"] == "banned_word"
    assert "summary" in response.json()["fields"]


def test_delete_pack(auth_client, draft):
    assert auth_client.delete(f"/api/v1/packs/{draft.slug}").status_code == 204
    assert not Pack.objects.exists()


def test_cover_upload_and_removal(auth_client, draft):
    image = BytesIO()
    Image.new("RGB", (1600, 900), "teal").save(image, format="PNG")
    upload = SimpleUploadedFile("cover.png", image.getvalue(), content_type="image/png")
    url = f"/api/v1/packs/{draft.slug}/cover"

    body = auth_client.put(url, {"cover": upload}, format="multipart").json()
    assert body["cover_url"].endswith(".webp")
    draft.refresh_from_db()
    assert Image.open(draft.cover).size == (1200, 630)

    body = auth_client.put(
        url, {"cover": SimpleUploadedFile("x.png", b"nope")}, format="multipart"
    ).json()
    assert body["fields"] == {"cover": ["Завантаж PNG, JPEG або WebP."]}

    assert auth_client.delete(url).json()["cover_url"] is None


# Fork, export, community


def test_fork_makes_a_draft_copy(api_client, user):
    original = PackFactory()
    add(original, mod(slug="sodium"))

    assert api_client.post(f"/api/v1/packs/{original.slug}/fork").status_code in (401, 403)
    response = client_for(user).post(f"/api/v1/packs/{original.slug}/fork")

    assert response.status_code == 201
    body = response.json()
    assert body["forked_from"] == {"slug": original.slug, "title": original.title}
    assert body["status"] == "draft"
    assert body["is_mine"] is True
    assert [item["project"]["slug"] for item in body["items"]] == ["sodium"]


def test_export_downloads_an_mrpack(api_client):
    pack = PackFactory(slug="sich")
    add(pack, mod(slug="sodium"))

    response = api_client.get("/api/v1/packs/sich/export.mrpack")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/x-modrinth-modpack+zip"
    assert response["Content-Disposition"] == 'attachment; filename="sich.mrpack"'
    with zipfile.ZipFile(BytesIO(response.content)) as archive:
        index = json.loads(archive.read("modrinth.index.json"))
    assert len(index["files"]) == 1
    pack.refresh_from_db()
    assert pack.downloads_count == 1


def test_export_of_an_official_pack_goes_to_modrinth(api_client):
    url = "https://cdn.modrinth.com/data/FABULOUS/versions/PACKV001/fo.mrpack"
    pack = PackFactory(is_official=True, modrinth_id="FABULOUS", source_file_url=url)

    response = api_client.get(f"/api/v1/packs/{pack.slug}/export.mrpack")

    assert response.status_code == 302
    assert response["Location"] == url
    pack.refresh_from_db()
    assert pack.downloads_count == 1


def test_export_without_a_loader_version_is_409(api_client):
    pack = PackFactory(loader_version="")

    response = api_client.get(f"/api/v1/packs/{pack.slug}/export.mrpack")

    assert response.status_code == 409
    assert response.json()["code"] == "no_loader_version"


def test_packs_can_be_reviewed_saved_and_reported(user):
    pack = PackFactory()
    client = client_for(user)

    review = client.put(
        "/api/v1/reviews",
        {"kind": "pack", "id": pack.slug, "stars": 5, "text": "Топ"},
        format="json",
    )
    favorite = client.post("/api/v1/favorites", {"kind": "pack", "id": pack.slug}, format="json")
    report = client.post(
        "/api/v1/reports",
        {"kind": "pack", "id": pack.slug, "reason": "spam"},
        format="json",
    )

    assert review.status_code in (200, 201), review.json()
    assert favorite.status_code in (200, 201), favorite.json()
    assert report.status_code == 201, report.json()
    assert Review.objects.count() == 1
    body = client.get(f"/api/v1/packs/{pack.slug}").json()
    assert (body["is_favorited"], body["my_review_stars"]) == (True, 5)


def test_owners_cannot_review_their_pack(user):
    pack = PackFactory(author=user)

    response = client_for(user).put(
        "/api/v1/reviews",
        {"kind": "pack", "id": pack.slug, "stars": 5, "text": "Я молодець"},
        format="json",
    )

    assert response.status_code in (400, 403)


def test_moderator_sees_pending_packs(user):
    pack = PackFactory(status=Pack.Status.PENDING)
    moderator = client_for(UserFactory(role=User.Role.MODERATOR))

    assert moderator.get(f"/api/v1/packs/{pack.slug}").status_code == 200
    assert PackItem.objects.count() == 0
