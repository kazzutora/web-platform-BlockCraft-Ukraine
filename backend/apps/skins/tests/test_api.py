import pytest
from rest_framework.test import APIClient

from apps.accounts.models import UserSettings
from apps.accounts.tests.factories import UserFactory
from apps.core.models import Source

from .factories import SkinFactory

pytestmark = pytest.mark.django_db


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_login(user)
    return client


def ids(response) -> list[int]:
    return [row["id"] for row in response.json()["results"]]


# Catalog


def test_catalog_hides_what_a_moderator_hid(api_client):
    shown = SkinFactory()
    SkinFactory(is_hidden=True)

    assert ids(api_client.get("/api/v1/skins")) == [shown.pk]


def test_catalog_filters(api_client):
    green = SkinFactory(color_bucket="green", model="slim", title="Мавка")
    mojang = SkinFactory(source=Source.MOJANG, player_name="Steve_UA", title="Steve_UA")

    assert ids(api_client.get("/api/v1/skins", {"color": "green"})) == [green.pk]
    assert ids(api_client.get("/api/v1/skins", {"model": "slim"})) == [green.pk]
    assert ids(api_client.get("/api/v1/skins", {"source": "mojang"})) == [mojang.pk]
    assert ids(api_client.get("/api/v1/skins", {"q": "мавк"})) == [green.pk]
    assert ids(api_client.get("/api/v1/skins", {"q": "steve_ua"})) == [mojang.pk]


def test_catalog_sorts(api_client):
    old = SkinFactory(favorites_count=9)
    new = SkinFactory()

    assert ids(api_client.get("/api/v1/skins"))[0] == old.pk
    assert ids(api_client.get("/api/v1/skins", {"sort": "new"}))[0] == new.pk


def test_catalog_has_no_n_plus_one(auth_client, django_assert_max_num_queries):
    SkinFactory.create_batch(6)

    with django_assert_max_num_queries(6):
        assert auth_client.get("/api/v1/skins").json()["count"] == 6


def test_cards_name_their_source(api_client):
    skin = SkinFactory()

    card = api_client.get("/api/v1/skins").json()["results"][0]

    assert card["source"] == {"name": "MineSkin", "url": skin.external_url}
    assert card["texture_url"].endswith(".png")


def test_download_gives_the_png_and_counts_it(api_client):
    skin = SkinFactory(title="Мавка")

    response = api_client.get(f"/api/v1/skins/{skin.pk}/download")

    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    assert "attachment" in response["Content-Disposition"]
    skin.refresh_from_db()
    assert skin.downloads_count == 1


def test_similar_skins_share_the_colour(api_client):
    skin = SkinFactory(color_bucket="green")
    same = SkinFactory(color_bucket="green")
    SkinFactory(color_bucket="red")

    data = api_client.get(f"/api/v1/skins/{skin.pk}/similar").json()

    assert [row["id"] for row in data] == [same.pk]


# «Мій скін»


def test_my_skin_shows_in_the_profile():
    user = UserFactory(nickname="Mavka")
    skin = SkinFactory()
    client = client_for(user)

    response = client.put("/api/v1/me/skin", {"skin_id": skin.pk}, format="json")

    assert response.status_code == 200
    assert response.json()["is_my_skin"] is True
    profile = APIClient().get("/api/v1/users/Mavka").json()
    assert profile["skin"]["id"] == skin.pk
    assert client.delete("/api/v1/me/skin").status_code == 204
    assert UserSettings.objects.get(user=user).skin is None


def test_a_hidden_skin_is_not_shown_in_the_profile():
    user = UserFactory(nickname="Mavka")
    skin = SkinFactory()
    client_for(user).put("/api/v1/me/skin", {"skin_id": skin.pk}, format="json")
    skin.is_hidden = True
    skin.save()

    assert APIClient().get("/api/v1/users/Mavka").json()["skin"] is None


def test_my_skin_needs_sign_in(api_client):
    assert api_client.put("/api/v1/me/skin", {"skin_id": 1}, format="json").status_code == 401


# Library


def test_saved_skins_list(auth_client):
    skin = SkinFactory(title="Мавка")
    auth_client.post("/api/v1/favorites", {"kind": "skin", "id": skin.pk}, format="json")

    results = auth_client.get("/api/v1/me/saved", {"kind": "skin"}).json()["results"]

    assert [(item["kind"], item["skin"]["title"]) for item in results] == [("skin", "Мавка")]


def test_skins_in_collections_show_cards_without_n_plus_one(
    auth_client, django_assert_max_num_queries
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

    assert all(item["skin"]["source"]["name"] for item in body["items"])
    assert len(body["preview"]) == 4
