from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

pytestmark = pytest.mark.django_db


def image_upload(size=(512, 300), image_format="PNG", name="avatar.png") -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", size, (79, 122, 52)).save(buffer, format=image_format)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f"image/{image_format.lower()}")


def test_me_requires_authentication(api_client):
    response = api_client.get("/api/v1/me")

    assert response.status_code == 401
    assert response.json() == {
        "detail": response.json()["detail"],
        "code": "not_authenticated",
        "fields": {},
    }


def test_me_returns_account_with_game_profile(auth_client, user):
    response = auth_client.get("/api/v1/me")

    assert response.status_code == 200
    data = response.json()
    assert data["nickname"] == user.nickname
    assert data["email"] == user.email
    assert data["avatar_url"] is None
    assert data["level"] == 1
    assert data["game_profile"] == {
        "game_version": "",
        "loader": "",
        "edition": "java",
        "interests": [],
        "onboarding_done": False,
    }


def test_update_bio_and_minecraft_nickname(auth_client):
    response = auth_client.patch(
        "/api/v1/me", {"bio": "Будую замки", "mc_nickname": "Steve_UA"}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["bio"] == "Будую замки"
    assert response.json()["mc_nickname"] == "Steve_UA"


def test_invalid_minecraft_nickname_is_reported_per_field(auth_client):
    response = auth_client.patch("/api/v1/me", {"mc_nickname": "no spaces!"}, format="json")

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "invalid"
    assert list(body["fields"]) == ["mc_nickname"]


def test_nickname_and_email_cannot_be_changed_through_me(auth_client, user):
    auth_client.patch("/api/v1/me", {"nickname": "Hacker", "email": "x@y.z"}, format="json")

    user.refresh_from_db()
    assert user.nickname != "Hacker"
    assert user.email != "x@y.z"


def test_onboarding_saves_choices(auth_client, user):
    response = auth_client.post(
        "/api/v1/me/onboarding",
        {
            "game_version": "26.3",
            "loader": "fabric",
            "edition": "java",
            "interests": ["building", "tech"],
        },
        format="json",
    )

    assert response.status_code == 200
    user.game_profile.refresh_from_db()
    assert user.game_profile.onboarding_done is True
    assert user.game_profile.game_version == "26.3"
    assert user.game_profile.interests == ["building", "tech"]


def test_onboarding_can_be_skipped(auth_client, user):
    response = auth_client.post("/api/v1/me/onboarding", {}, format="json")

    assert response.status_code == 200
    user.game_profile.refresh_from_db()
    assert user.game_profile.onboarding_done is True
    assert user.game_profile.game_version == ""


def test_game_profile_rejects_unknown_version_and_loader(auth_client):
    response = auth_client.patch(
        "/api/v1/me/game-profile",
        {"game_version": "9.99", "loader": "optifine", "interests": ["sleeping"]},
        format="json",
    )

    assert response.status_code == 400
    assert set(response.json()["fields"]) == {"game_version", "loader", "interests.0"}


def test_settings_can_be_read_and_changed(auth_client):
    assert auth_client.get("/api/v1/me/settings").json()["theme"] == "light"

    response = auth_client.patch(
        "/api/v1/me/settings",
        {"theme": "dark", "who_can_comment": "nobody", "collections_visible": False},
        format="json",
    )

    assert response.status_code == 200
    assert response.json() | {"notify_prefs": {}} == {
        "theme": "dark",
        "language": "uk",
        "notify_prefs": {},
        "history_enabled": True,
        "who_can_comment": "nobody",
        "collections_visible": False,
    }


def test_avatar_is_cropped_to_square_webp(auth_client, user):
    response = auth_client.put("/api/v1/me/avatar", {"avatar": image_upload()}, format="multipart")

    assert response.status_code == 200
    assert response.json()["avatar_url"].endswith(".webp")
    user.refresh_from_db()
    with Image.open(user.avatar.path) as saved:
        assert saved.size == (256, 256)
        assert saved.format == "WEBP"


def test_replacing_avatar_deletes_the_old_file(auth_client, user):
    auth_client.put("/api/v1/me/avatar", {"avatar": image_upload()}, format="multipart")
    user.refresh_from_db()
    first = user.avatar.path

    auth_client.put("/api/v1/me/avatar", {"avatar": image_upload()}, format="multipart")

    user.refresh_from_db()
    assert user.avatar.path != first
    assert not user.avatar.storage.exists(first)


def test_avatar_rejects_files_that_are_not_images(auth_client):
    fake = SimpleUploadedFile("avatar.png", b"definitely not a png", content_type="image/png")

    response = auth_client.put("/api/v1/me/avatar", {"avatar": fake}, format="multipart")

    assert response.status_code == 400
    assert response.json()["code"] == "avatar_invalid"
    assert "avatar" in response.json()["fields"]


def test_avatar_can_be_removed(auth_client, user):
    auth_client.put("/api/v1/me/avatar", {"avatar": image_upload()}, format="multipart")

    response = auth_client.delete("/api/v1/me/avatar")

    assert response.status_code == 200
    assert response.json()["avatar_url"] is None
