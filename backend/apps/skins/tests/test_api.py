import pytest
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.skins.models import Skin

from .factories import SkinFactory

pytestmark = pytest.mark.django_db


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_login(user)
    return client


# Catalog


def test_catalog_shows_only_published_skins(api_client):
    SkinFactory(title="Видимий")
    SkinFactory(title="Чекає", status=Skin.Status.PENDING)
    SkinFactory(title="Відхилений", status=Skin.Status.REJECTED)

    titles = [skin["title"] for skin in api_client.get("/api/v1/skins").json()["results"]]

    assert titles == ["Видимий"]


def test_catalog_filters(api_client):
    author = UserFactory(nickname="Mavka")
    SkinFactory(title="Синій", color_bucket="blue", author=author)
    SkinFactory(title="Тонкий", model=Skin.Model.SLIM, style_tags=["anime"])
    SkinFactory(title="Козак", style_tags=["ukrainian", "medieval"])

    def titles(**params):
        page = api_client.get("/api/v1/skins", params).json()
        return {skin["title"] for skin in page["results"]}

    assert titles(color="blue") == {"Синій"}
    assert titles(model="slim") == {"Тонкий"}
    assert titles(style="ukrainian,anime") == {"Тонкий", "Козак"}
    assert titles(author="mavka") == {"Синій"}
    assert titles(q="коз") == {"Козак"}


def test_catalog_sorts(api_client):
    SkinFactory(title="Популярний", downloads_count=50)
    SkinFactory(title="Улюблений", favorites_count=30)

    first = api_client.get("/api/v1/skins").json()["results"][0]["title"]
    top = api_client.get("/api/v1/skins", {"sort": "top"}).json()["results"][0]["title"]

    assert (first, top) == ("Популярний", "Улюблений")


def test_catalog_has_no_n_plus_one(auth_client, django_assert_max_num_queries):
    SkinFactory.create_batch(12)

    with django_assert_max_num_queries(5):
        response = auth_client.get("/api/v1/skins")

    assert len(response.json()["results"]) == 12


def test_viewer_state_on_cards(user, auth_client):
    skin = SkinFactory()
    auth_client.post("/api/v1/favorites", {"kind": "skin", "id": skin.pk}, format="json")

    card = auth_client.get("/api/v1/skins").json()["results"][0]

    assert (card["is_favorited"], card["favorites_count"]) == (True, 1)


# Detail


def test_pending_skin_is_visible_only_to_its_author(api_client):
    skin = SkinFactory(status=Skin.Status.PENDING)

    assert api_client.get(f"/api/v1/skins/{skin.pk}").status_code == 404
    assert client_for(UserFactory()).get(f"/api/v1/skins/{skin.pk}").status_code == 404
    assert client_for(skin.author).get(f"/api/v1/skins/{skin.pk}").status_code == 200


def test_download_gives_the_png_and_counts_it(api_client):
    skin = SkinFactory(title="Козак")

    response = api_client.get(f"/api/v1/skins/{skin.pk}/download")

    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    assert "attachment" in response["Content-Disposition"]
    assert b"".join(response.streaming_content).startswith(b"\x89PNG")
    skin.refresh_from_db()
    assert skin.downloads_count == 1


def test_similar_skins_share_colour_or_style(api_client):
    skin = SkinFactory(color_bucket="green", style_tags=["fantasy"])
    SkinFactory(title="Той самий колір", color_bucket="green")
    SkinFactory(title="Той самий стиль", color_bucket="red", style_tags=["fantasy"])
    SkinFactory(title="Інший", color_bucket="red")

    titles = {s["title"] for s in api_client.get(f"/api/v1/skins/{skin.pk}/similar").json()}

    assert titles == {"Той самий колір", "Той самий стиль"}


# The profile


def test_current_skin_shows_in_the_profile():
    author = UserFactory(nickname="Mavka")
    first, second = SkinFactory(author=author), SkinFactory(author=author)
    client = client_for(author)

    client.put("/api/v1/me/skin", {"skin_id": first.pk}, format="json")
    response = client.put("/api/v1/me/skin", {"skin_id": second.pk}, format="json")

    assert response.json()["is_current"] is True
    first.refresh_from_db()
    assert first.is_current is False
    profile = APIClient().get("/api/v1/users/Mavka").json()
    assert profile["skin"] == {
        "id": second.pk,
        "texture_url": second.file.url,
        "model": "classic",
    }

    assert client.delete("/api/v1/me/skin").status_code == 204
    assert APIClient().get("/api/v1/users/Mavka").json()["skin"] is None


def test_someone_elses_skin_cannot_be_current(auth_client):
    skin = SkinFactory()

    response = auth_client.put("/api/v1/me/skin", {"skin_id": skin.pk}, format="json")

    assert response.status_code == 403


def test_pending_current_skin_is_not_public_yet():
    author = UserFactory(nickname="Nova")
    skin = SkinFactory(author=author, status=Skin.Status.PENDING)
    client_for(author).put("/api/v1/me/skin", {"skin_id": skin.pk}, format="json")

    assert APIClient().get("/api/v1/users/Nova").json()["skin"] is None


# Library


def test_saved_skins_list(user, auth_client):
    skin = SkinFactory(title="Мавка")
    auth_client.post("/api/v1/favorites", {"kind": "skin", "id": skin.pk}, format="json")

    results = auth_client.get("/api/v1/me/saved", {"kind": "skin"}).json()["results"]

    assert [(item["kind"], item["skin"]["title"]) for item in results] == [("skin", "Мавка")]


def test_skins_in_collections_show_cards_without_n_plus_one(
    user, auth_client, django_assert_max_num_queries
):
    collection_id = auth_client.post(
        "/api/v1/collections", {"title": "Скіни на вечір"}, format="json"
    ).json()["id"]
    for skin in SkinFactory.create_batch(5):
        auth_client.post(
            f"/api/v1/collections/{collection_id}/items",
            {"kind": "skin", "id": skin.pk},
            format="json",
        )

    with django_assert_max_num_queries(12):
        body = auth_client.get(f"/api/v1/collections/{collection_id}").json()

    assert all(item["skin"]["author"]["nickname"] for item in body["items"])
    assert len(body["preview"]) == 4
