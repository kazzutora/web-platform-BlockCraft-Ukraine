import json

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.tests.factories import UserFactory
from apps.core.kinds import get_kind
from apps.library.models import Favorite
from apps.mods.models import Project
from apps.mods.tests.factories import ProjectFactory
from apps.packs.models import Pack
from apps.packs.tests.factories import PackFactory
from apps.servers.tests.factories import ServerFactory
from apps.skins.models import Skin
from apps.skins.tests.factories import SkinFactory
from apps.social import services as social
from apps.social.models import Review

pytestmark = pytest.mark.django_db


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_login(user)
    return client


@pytest.fixture
def player():
    user = UserFactory(nickname="Mavka", bio="Будую замки")
    project = ProjectFactory(slug="sodium")
    social.upsert_review(user=user, kind="mod", identifier="sodium", stars=5, text="Топ")
    Favorite.objects.create(
        user=user, content_type=get_kind("mod").content_type, object_id=project.pk
    )
    Project.objects.filter(pk=project.pk).update(favorites_count=1)
    server = ServerFactory()
    social.upsert_review(user=user, kind="server", identifier=server.slug, stars=4, text="Ок")
    SkinFactory(author=user, title="Мій скін")
    original = PackFactory(slug="original", forks_count=1)
    PackFactory(author=user, slug="my-fork", forked_from=original)
    return user


def test_export_contains_everything_about_the_player(player):
    response = client_for(player).get("/api/v1/me/export")

    assert response.status_code == 200
    assert "attachment" in response["Content-Disposition"]
    data = json.loads(response.content)
    assert data["account"]["nickname"] == "Mavka"
    reviews = {r["id"]: r for r in data["reviews"]}
    assert reviews["sodium"] == {**reviews["sodium"], "kind": "mod", "stars": 5}
    assert data["favorites"][0]["id"] == "sodium"
    assert {r["id"] for r in data["reviews"]} == {
        "sodium",
        ServerFactory._meta.model.objects.get().slug,
    }
    assert data["skins"][0]["title"] == "Мій скін"
    assert data["packs"][0] == {**data["packs"][0], "slug": "my-fork", "mods": []}


def test_delete_needs_the_nickname(player):
    response = client_for(player).delete("/api/v1/me?mode=delete&confirm=Someone")

    assert response.json()["code"] == "confirm_mismatch"
    assert User.objects.filter(pk=player.pk).exists()


def test_anonymize_keeps_content_without_the_person(player):
    client = client_for(player)

    assert client.delete("/api/v1/me?mode=anonymize&confirm=mavka").status_code == 204

    player.refresh_from_db()
    assert player.nickname == f"deleted_{player.pk}"
    assert (player.email.endswith("@deleted.invalid"), player.is_active, player.bio) == (
        True,
        False,
        "",
    )
    assert not player.has_usable_password()
    assert Skin.objects.filter(author=player).exists()
    assert Review.objects.filter(user=player).count() == 2
    assert client.get("/api/v1/me").status_code == 401


def test_delete_removes_everything_and_fixes_counters(player):
    sodium = Project.objects.get(slug="sodium")
    assert (sodium.rating_count, sodium.favorites_count) == (1, 1)

    assert client_for(player).delete("/api/v1/me?mode=delete&confirm=Mavka").status_code == 204

    assert not User.objects.filter(pk=player.pk).exists()
    assert not Skin.objects.exists()
    sodium.refresh_from_db()
    assert (sodium.rating_count, sodium.rating_avg, sodium.favorites_count) == (0, 0, 0)
    server = ServerFactory._meta.model.objects.get()
    assert server.rating_count == 0
    assert Pack.objects.get().forks_count == 0
