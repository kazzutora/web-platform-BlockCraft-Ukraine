import json

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.tests.factories import UserFactory
from apps.core.kinds import get_kind
from apps.library.models import Favorite
from apps.mods.models import Project
from apps.mods.tests.factories import ProjectFactory
from apps.servers.tests.factories import ServerFactory
from apps.skins.models import Skin
from apps.skins.tests.factories import SkinFactory
from apps.social import services as social
from apps.social.models import Comment

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
    social.add_comment(user=user, kind="server", identifier=server.slug, body="Класний сервер")
    SkinFactory(author=user, title="Мій скін")
    return user


def test_export_contains_everything_about_the_player(player):
    response = client_for(player).get("/api/v1/me/export")

    assert response.status_code == 200
    assert "attachment" in response["Content-Disposition"]
    data = json.loads(response.content)
    assert data["account"]["nickname"] == "Mavka"
    assert data["reviews"][0] == {**data["reviews"][0], "kind": "mod", "id": "sodium", "stars": 5}
    assert data["favorites"][0]["id"] == "sodium"
    assert data["comments"][0]["body"] == "Класний сервер"
    assert data["skins"][0]["title"] == "Мій скін"


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
    assert Comment.objects.filter(user=player).exists()
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
    assert server.comments_count == 0
