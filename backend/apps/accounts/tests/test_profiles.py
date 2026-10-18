import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import GameProfile, User, UserSettings

from .factories import UserFactory

pytestmark = pytest.mark.django_db


def test_profiles_are_created_for_every_new_user():
    user = get_user_model().objects.create_user(
        email="Alex@Example.com", password="x", nickname="Alex"
    )

    assert user.email == "alex@example.com"
    assert GameProfile.objects.filter(user=user).exists()
    assert UserSettings.objects.filter(user=user).exists()


def test_superuser_gets_admin_role_and_profiles():
    admin = User.objects.create_superuser(email="root@example.com", password="x", nickname="Root")

    assert admin.role == User.Role.ADMIN
    assert admin.is_moderator
    assert hasattr(admin, "game_profile")


def test_open_profile_is_visible_to_guests(api_client):
    UserFactory(nickname="Steve_UA", bio="Будую замки", mc_nickname="Steve")

    response = api_client.get("/api/v1/users/steve_ua")

    assert response.status_code == 200
    data = response.json()
    assert data["nickname"] == "Steve_UA"
    assert data["is_private"] is False
    assert data["bio"] == "Будую замки"
    assert data["level"] == 1


def test_closed_profile_shows_only_nickname_to_others(api_client, auth_client):
    UserFactory(nickname="Hidden", bio="секрет", is_private=True)

    for client in (api_client, auth_client):
        data = client.get("/api/v1/users/Hidden").json()
        assert data["nickname"] == "Hidden"
        assert data["is_private"] is True
        assert data["bio"] is None
        assert data["level"] is None
        assert data["date_joined"] is None


def test_closed_profile_is_full_for_owner_and_moderators(api_client):
    owner = UserFactory(nickname="Hidden", bio="секрет", is_private=True)
    moderator = UserFactory(role=User.Role.MODERATOR)

    for viewer in (owner, moderator):
        api_client.force_login(viewer)
        assert api_client.get("/api/v1/users/Hidden").json()["bio"] == "секрет"


def test_unknown_or_inactive_profile_is_404(api_client):
    UserFactory(nickname="Gone", is_active=False)

    for nickname in ("Gone", "Nobody"):
        response = api_client.get(f"/api/v1/users/{nickname}")
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
