"""Registration, email confirmation, sign-in and sign-out through allauth headless."""

import re
from urllib.parse import unquote

import pytest

from apps.accounts.models import GameProfile, User, UserSettings

from .factories import PASSWORD, UserFactory

pytestmark = pytest.mark.django_db

AUTH = "/_allauth/browser/v1/auth"


def signup(client, **data):
    payload = {"email": "steve@example.com", "username": "Steve_UA", "password": PASSWORD} | data
    return client.post(f"{AUTH}/signup", payload, format="json")


def pending_flow(response) -> str | None:
    flows = response.json().get("data", {}).get("flows", [])
    return next((flow["id"] for flow in flows if flow.get("is_pending")), None)


def test_signup_creates_user_with_profiles_and_asks_to_confirm_email(api_client, mailoutbox):
    response = signup(api_client)

    assert response.status_code == 401
    assert pending_flow(response) == "verify_email"
    user = User.objects.get(email="steve@example.com")
    assert user.nickname == "Steve_UA"
    assert GameProfile.objects.filter(user=user, onboarding_done=False).exists()
    assert UserSettings.objects.filter(user=user, theme="light").exists()
    assert len(mailoutbox) == 1
    assert "http://localhost:8080/verify-email/" in mailoutbox[0].body


def test_confirming_email_signs_the_user_in(api_client, mailoutbox):
    signup(api_client)
    key = unquote(re.search(r"/verify-email/(\S+)", mailoutbox[0].body).group(1))

    response = api_client.post(f"{AUTH}/email/verify", {"key": key}, format="json")

    assert response.status_code == 200
    me = api_client.get("/api/v1/me")
    assert me.status_code == 200
    assert me.json()["nickname"] == "Steve_UA"


@pytest.mark.parametrize(
    ("nickname", "reason"),
    [
        ("ab", "too short"),
        ("Стів", "cyrillic"),
        ("steve.ua", "dot"),
        ("x" * 25, "too long"),
        ("Admin", "reserved"),
        ("NotAFuckingNick", "banned word"),
    ],
)
def test_signup_rejects_invalid_nicknames(api_client, nickname, reason):
    response = signup(api_client, username=nickname)

    assert response.status_code == 400, reason
    params = [error.get("param") for error in response.json()["errors"]]
    assert "username" in params
    assert not User.objects.filter(email="steve@example.com").exists()


def test_signup_rejects_taken_nickname_in_any_case(api_client):
    UserFactory(nickname="Steve_UA")

    response = signup(api_client, username="steve_ua")

    assert response.status_code == 400
    assert [error["param"] for error in response.json()["errors"]] == ["username"]


def test_login_with_email_and_logout(api_client):
    user = UserFactory()

    response = api_client.post(
        f"{AUTH}/login", {"email": user.email, "password": PASSWORD}, format="json"
    )
    assert response.status_code == 200
    assert api_client.get("/api/v1/me").status_code == 200

    response = api_client.delete(f"{AUTH}/session")
    assert response.status_code == 401
    assert api_client.get("/api/v1/me").status_code == 401


def test_login_with_wrong_password_fails(api_client):
    user = UserFactory()

    response = api_client.post(
        f"{AUTH}/login", {"email": user.email, "password": "wrong-password"}, format="json"
    )

    assert response.status_code == 400
    assert api_client.get("/api/v1/me").status_code == 401


def test_login_requires_confirmed_email(api_client, mailoutbox):
    user = UserFactory(verified=False)

    response = api_client.post(
        f"{AUTH}/login", {"email": user.email, "password": PASSWORD}, format="json"
    )

    assert response.status_code == 401
    assert pending_flow(response) == "verify_email"
    assert api_client.get("/api/v1/me").status_code == 401


def test_password_reset_by_email_link(api_client, mailoutbox):
    user = UserFactory()

    response = api_client.post(f"{AUTH}/password/request", {"email": user.email}, format="json")
    assert response.status_code == 200
    key = unquote(re.search(r"/password-reset/(\S+)", mailoutbox[0].body).group(1))

    response = api_client.post(
        f"{AUTH}/password/reset", {"key": key, "password": "Brand-New-Pass-2026"}, format="json"
    )

    assert response.status_code in {200, 401}
    user.refresh_from_db()
    assert user.check_password("Brand-New-Pass-2026")


def test_config_lists_only_configured_providers(api_client):
    response = api_client.get("/_allauth/browser/v1/config")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["account"]["login_methods"] == ["email"]
    assert data["socialaccount"]["providers"] == []
