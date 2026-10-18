import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.tests.factories import UserFactory
from apps.skins import services
from apps.skins.models import Skin

from .factories import SkinFactory, png_bytes, skin_image, skin_png

pytestmark = pytest.mark.django_db


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_login(user)
    return client


def upload(client, data: bytes | None = None, **fields):
    payload = {
        "file": SimpleUploadedFile("skin.png", data or skin_png(), content_type="image/png"),
        "title": "Козак у вишиванці",
        **fields,
    }
    return client.post("/api/v1/skins", payload, format="multipart")


# Upload


def test_new_author_upload_waits_for_moderation_with_detected_traits(
    auth_client, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        response = upload(
            auth_client,
            skin_png(color=(40, 70, 220), slim=True),
            style_tags=["ukrainian", "casual"],
        )

    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["status"] == "pending"
    assert (body["model"], body["color_bucket"]) == ("slim", "blue")
    assert body["style_tags"] == ["ukrainian", "casual"]
    assert body["is_mine"] is True
    skin = Skin.objects.get(pk=body["id"])
    with skin.preview.open("rb") as file:
        assert Image.open(file).size == (128, 256)


def test_uploaded_texture_is_stored_as_64x64_png(auth_client):
    legacy = skin_image().crop((0, 0, 64, 32))

    response = upload(auth_client, png_bytes(legacy))

    skin = Skin.objects.get(pk=response.json()["id"])
    with skin.file.open("rb") as file:
        assert Image.open(file).size == (64, 64)


def test_authors_with_three_published_works_publish_right_away(user, auth_client):
    User.objects.filter(pk=user.pk).update(published_count=3)

    body = upload(auth_client).json()

    assert body["status"] == "published"
    user.refresh_from_db()
    assert user.published_count == 4


def test_trusted_authors_skip_moderation():
    trusted = UserFactory(role=User.Role.TRUSTED)

    assert upload(client_for(trusted)).json()["status"] == "published"


def test_the_model_can_be_chosen_by_hand(auth_client):
    body = upload(auth_client, skin_png(slim=True), model="classic").json()

    assert body["model"] == "classic"


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (b"not a png", "skin_invalid"),
        (png_bytes(Image.new("RGBA", (64, 48))), "skin_wrong_size"),
    ],
)
def test_broken_files_are_rejected_with_a_field_error(auth_client, data, code):
    response = upload(auth_client, data)

    assert response.status_code == 400
    assert response.json()["code"] == code
    assert "file" in response.json()["fields"]


def test_the_same_skin_twice_is_rejected(auth_client):
    upload(auth_client)

    response = upload(auth_client)

    assert response.json()["code"] == "skin_duplicate"


def test_at_most_three_styles(auth_client):
    response = upload(auth_client, style_tags=["anime", "cute", "mob", "sport"])

    assert response.status_code == 400
    assert "style_tags" in response.json()["fields"]


def test_guests_cannot_upload(api_client):
    assert upload(api_client).status_code == 401


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
    SkinFactory(title="Улюблений", likes_count=30)

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
    auth_client.post("/api/v1/likes", {"kind": "skin", "id": skin.pk}, format="json")
    auth_client.post("/api/v1/favorites", {"kind": "skin", "id": skin.pk}, format="json")

    card = auth_client.get("/api/v1/skins").json()["results"][0]

    assert (card["is_liked"], card["likes_count"]) == (True, 1)
    assert (card["is_favorited"], card["favorites_count"]) == (True, 1)


# Detail, edit, delete


def test_pending_skin_is_visible_only_to_its_author(api_client):
    skin = SkinFactory(status=Skin.Status.PENDING)

    assert api_client.get(f"/api/v1/skins/{skin.pk}").status_code == 404
    assert client_for(UserFactory()).get(f"/api/v1/skins/{skin.pk}").status_code == 404
    assert client_for(skin.author).get(f"/api/v1/skins/{skin.pk}").status_code == 200


def test_author_edits_title_styles_and_model(django_capture_on_commit_callbacks):
    skin = SkinFactory(file__data=skin_png(slim=True))
    client = client_for(skin.author)

    with django_capture_on_commit_callbacks(execute=True):
        response = client.patch(
            f"/api/v1/skins/{skin.pk}",
            {"title": "  Новий  ", "style_tags": ["cute"], "model": "slim"},
            format="json",
        )

    assert response.status_code == 200
    body = response.json()
    assert (body["title"], body["style_tags"], body["model"]) == ("Новий", ["cute"], "slim")
    skin.refresh_from_db()
    assert skin.preview  # re-rendered for the new arm width


def test_others_cannot_edit_or_delete():
    skin = SkinFactory()
    client = client_for(UserFactory())

    assert (
        client.patch(f"/api/v1/skins/{skin.pk}", {"title": "Моє"}, format="json").status_code == 403
    )
    assert client.delete(f"/api/v1/skins/{skin.pk}").status_code == 403


def test_author_deletes_a_published_skin(django_capture_on_commit_callbacks):
    author = UserFactory(published_count=1)
    skin = SkinFactory(author=author)
    storage, name = skin.file.storage, skin.file.name

    with django_capture_on_commit_callbacks(execute=True):
        response = client_for(author).delete(f"/api/v1/skins/{skin.pk}")

    assert response.status_code == 204

    assert not Skin.objects.exists()
    assert not storage.exists(name)
    author.refresh_from_db()
    assert author.published_count == 0


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


# Moderation


def test_approval_publishes_and_counts_for_the_author():
    skin = SkinFactory(status=Skin.Status.PENDING, published_at=None)

    services.approve(skin=skin)

    skin.refresh_from_db()
    skin.author.refresh_from_db()
    assert skin.status == Skin.Status.PUBLISHED
    assert skin.published_at is not None
    assert skin.author.published_count == 1


def test_rejection_keeps_the_reason():
    skin = SkinFactory(status=Skin.Status.PENDING)

    services.reject(skin=skin, reason="Чужий скін")

    skin.refresh_from_db()
    assert (skin.status, skin.rejection_reason) == (Skin.Status.REJECTED, "Чужий скін")


# My skins and the profile


def test_my_skins_include_every_status():
    author = UserFactory()
    SkinFactory(author=author, status=Skin.Status.PENDING)
    SkinFactory(author=author, status=Skin.Status.REJECTED, rejection_reason="Не скін")
    SkinFactory()

    results = client_for(author).get("/api/v1/me/skins").json()["results"]

    assert sorted(skin["status"] for skin in results) == ["pending", "rejected"]


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
