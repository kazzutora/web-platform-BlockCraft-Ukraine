from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import GameProfile
from apps.accounts.tests.factories import UserFactory
from apps.core.kinds import get_kind
from apps.library.models import Favorite
from apps.mods.tests.factories import ProjectFactory
from apps.servers import status
from apps.servers.tests.factories import ServerFactory, SnapshotFactory, online
from apps.skins.tests.factories import SkinFactory
from apps.social.models import Like

pytestmark = pytest.mark.django_db


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_login(user)
    return client


@pytest.fixture
def content():
    ProjectFactory(slug="sodium", game_versions=["26.3"], loaders=["fabric"], trend_score=5)
    ProjectFactory(slug="forge-only", game_versions=["26.3"], loaders=["forge"], trend_score=9)
    ProjectFactory(slug="old", game_versions=["1.20.1"], loaders=["fabric"], trend_score=7)
    busy, quiet = ServerFactory(name="Людно"), ServerFactory(name="Тихо")
    SnapshotFactory(server=busy, players_online=90)
    SnapshotFactory(server=quiet, players_online=4)
    status.store({busy.pk: online(players=90), quiet.pk: online(players=4)})
    week = timezone.now() - timedelta(days=2)
    SkinFactory(title="Вчорашній", trend_score=3, published_at=week)
    SkinFactory(title="Хіт тижня", trend_score=8, published_at=week)
    SkinFactory(
        title="Торішній хіт", trend_score=50, published_at=timezone.now() - timedelta(days=300)
    )


def test_guests_get_popular_mods_and_the_common_blocks(api_client, content):
    body = api_client.get("/api/v1/home").json()

    assert body["for_you"]["basis"] == "popular"
    assert [m["slug"] for m in body["for_you"]["mods"]] == ["forge-only", "old", "sodium"]
    assert body["skin_of_week"]["title"] == "Хіт тижня"
    assert [s["name"] for s in body["servers_online"]] == ["Людно", "Тихо"]
    assert body["servers_online"][0]["live"]["players_online"] == 90
    assert len(body["new_skins"]) == 3


def test_players_get_mods_for_their_version_and_loader(content):
    user = UserFactory()
    GameProfile.objects.filter(user=user).update(game_version="26.3", loader="fabric")

    body = client_for(user).get("/api/v1/home").json()

    assert body["for_you"] == {**body["for_you"], "basis": "profile", "game_version": "26.3"}
    assert [m["slug"] for m in body["for_you"]["mods"]] == ["sodium"]


def test_viewer_state_is_personal_even_with_the_cache(content):
    first, second = UserFactory(), UserFactory()
    skin = SkinFactory(title="Найновіший", published_at=timezone.now())
    Favorite.objects.create(
        user=first, content_type=get_kind("skin").content_type, object_id=skin.pk
    )

    client_for(second).get("/api/v1/home")  # fills the cache
    mine = client_for(first).get("/api/v1/home").json()["new_skins"][0]
    theirs = client_for(second).get("/api/v1/home").json()["new_skins"][0]

    assert (mine["title"], mine["is_favorited"], theirs["is_favorited"]) == (
        "Найновіший",
        True,
        False,
    )


def test_home_is_cached(api_client, content, django_assert_max_num_queries):
    api_client.get("/api/v1/home")

    # Cached: only the per-viewer reads by id are left
    with django_assert_max_num_queries(8):
        api_client.get("/api/v1/home")


def test_top_periods(api_client):
    trending = ProjectFactory(slug="trending", trend_score=10, score=3)
    rated = ProjectFactory(slug="rated", trend_score=0, score=4.9)
    ProjectFactory(slug="quiet", trend_score=0, score=1)
    ct = get_kind("mod").content_type
    for _ in range(3):
        Favorite.objects.create(user=UserFactory(), content_type=ct, object_id=rated.pk)

    def slugs(period):
        body = api_client.get("/api/v1/top", {"kind": "mod", "period": period}).json()
        assert body["skins"] == [] and body["servers"] == []
        return [m["slug"] for m in body["mods"]]

    assert slugs("week") == ["trending"]
    assert slugs("month") == ["rated"]
    assert slugs("all")[:2] == ["rated", "trending"]
    assert trending.pk


def test_top_skins_and_servers(api_client):
    skin = SkinFactory(trend_score=2)
    Like.objects.create(
        user=UserFactory(), content_type=get_kind("skin").content_type, object_id=skin.pk
    )
    server = ServerFactory(trend_score=1)
    status.store({server.pk: online(players=12)})

    assert (
        api_client.get("/api/v1/top", {"kind": "skin", "period": "month"}).json()["skins"][0]["id"]
        == skin.pk
    )
    servers = api_client.get("/api/v1/top", {"kind": "server"}).json()["servers"]
    assert servers[0]["live"]["players_online"] == 12
    assert api_client.get("/api/v1/top", {"period": "year"}).status_code == 400
