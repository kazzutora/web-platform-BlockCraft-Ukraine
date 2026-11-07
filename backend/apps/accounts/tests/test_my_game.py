"""«Моя гра»: the profile of a player, the `bc_game` cookie of a guest (docs/tech.md, 10.2)."""

import pytest
from django.test import RequestFactory

from apps.accounts import services
from apps.core.game import GAME_COOKIE, GameContext, game_context, parse_game_cookie

from .factories import PASSWORD, UserFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("game_versions")]

URL = "/api/v1/me/game"
LOGIN = "/_allauth/browser/v1/auth/login"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1.21.1:fabric", ("1.21.1", "fabric")),
        ("1.21.1%3Afabric", ("1.21.1", "fabric")),  # as the browser encodes it
        ("26.3:", ("26.3", "")),
        (":neoforge", ("", "neoforge")),
        (":", None),
        ("1.21.1:optifine", None),
        ("1.21.1", None),
        ("<script>:fabric", None),
        ("", None),
        (None, None),
    ],
)
def test_cookie_shape(value, expected):
    assert parse_game_cookie(value) == expected


def request_with(cookie: str | None = None, user=None):
    request = RequestFactory().get("/")
    if cookie is not None:
        request.COOKIES[GAME_COOKIE] = cookie
    if user is not None:
        request.user = user
    return request


def test_guest_context_comes_from_the_cookie():
    assert game_context(request_with("1.21.1:fabric")) == GameContext("1.21.1", "fabric", "cookie")
    assert game_context(request_with()) == GameContext()


def test_unsupported_cookie_version_is_dropped():
    assert game_context(request_with("1.15.2:fabric")) == GameContext("", "fabric", "cookie")
    assert game_context(request_with("1.15.2:")) == GameContext()


def test_the_profile_wins_once_it_has_a_choice(user):
    services.update_game_profile(user=user, data={"loader": "forge"})

    context = game_context(request_with("1.21.1:fabric", user=user))

    assert context == GameContext("", "forge", "profile")


def test_a_player_with_an_empty_profile_keeps_the_cookie(user):
    assert game_context(request_with("26.3:quilt", user=user)).source == "cookie"


def test_guests_cannot_use_the_endpoint(api_client):
    assert api_client.get(URL).status_code == 401
    assert api_client.put(URL, {"game_version": "1.21.1"}).status_code == 401


def test_player_reads_and_changes_my_game(auth_client):
    assert auth_client.get(URL).json()["game_version"] is None

    body = auth_client.put(URL, {"game_version": "1.21.1", "loader": "fabric"}).json()
    assert (body["game_version"], body["loader"]) == ("1.21.1", "fabric")

    body = auth_client.patch(URL, {"loader": "neoforge"}).json()
    assert (body["game_version"], body["loader"]) == ("1.21.1", "neoforge")


def test_unknown_versions_and_loaders_are_refused(auth_client):
    response = auth_client.put(URL, {"game_version": "9.99", "loader": "optifine"})

    assert response.status_code == 400
    assert set(response.json()["fields"]) == {"game_version", "loader"}


def test_signing_in_adopts_the_guest_choice(api_client):
    user = UserFactory()
    api_client.cookies[GAME_COOKIE] = "1.21.1:fabric"

    response = api_client.post(LOGIN, {"email": user.email, "password": PASSWORD}, format="json")

    assert response.status_code == 200
    user.game_profile.refresh_from_db()
    assert (user.game_profile.game_version_id, user.game_profile.loader) == ("1.21.1", "fabric")


def test_signing_in_never_overwrites_the_profile(api_client):
    user = UserFactory()
    services.update_game_profile(user=user, data={"loader": "forge"})
    api_client.cookies[GAME_COOKIE] = "1.21.1:fabric"

    api_client.post(LOGIN, {"email": user.email, "password": PASSWORD}, format="json")

    user.game_profile.refresh_from_db()
    assert (user.game_profile.game_version_id, user.game_profile.loader) == (None, "forge")


def test_a_broken_cookie_changes_nothing(user):
    assert not services.adopt_guest_game(user=user, cookie="9.99:")
    assert not services.adopt_guest_game(user=user, cookie="garbage")


def test_put_replaces_my_game_and_patch_changes_one_part(auth_client):
    auth_client.put(URL, {"game_version": "1.21.1", "loader": "fabric"})

    assert auth_client.patch(URL, {"loader": "quilt"}).json()["game_version"] == "1.21.1"
    body = auth_client.put(URL, {"loader": "forge"}, format="json").json()
    assert (body["game_version"], body["loader"]) == (None, "forge")


def test_only_changes_are_throttled(auth_client, monkeypatch):
    from rest_framework.throttling import ScopedRateThrottle

    monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", {"game": "2/hour"})

    assert [auth_client.patch(URL, {"loader": "fabric"}).status_code for _ in range(3)] == [
        200,
        200,
        429,
    ]
    assert auth_client.get(URL).status_code == 200
