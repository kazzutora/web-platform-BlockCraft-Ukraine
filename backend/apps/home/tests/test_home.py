from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import GameProfile
from apps.accounts.tests.factories import UserFactory
from apps.core.game import GAME_COOKIE
from apps.core.kinds import get_kind
from apps.home import selectors
from apps.library.models import Favorite
from apps.mods.tests.factories import ProjectFactory
from apps.packs.tests.factories import PackFactory
from apps.servers import status
from apps.servers.tests.factories import ServerFactory, SnapshotFactory, online
from apps.skins.models import Skin
from apps.skins.tests.factories import SkinFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("game_versions")]


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_login(user)
    return client


@pytest.fixture
def content():
    ProjectFactory(slug="sodium", game_versions=["26.3"], loaders=["fabric"], trend_score=5)
    ProjectFactory(slug="forge-only", game_versions=["26.3"], loaders=["forge"], trend_score=9)
    ProjectFactory(slug="old", game_versions=["1.20.1"], loaders=["fabric"], trend_score=7)
    ProjectFactory(
        slug="faithful",
        project_type="resourcepack",
        game_versions=["26.3"],
        loaders=["minecraft"],
        trend_score=1,
    )
    busy, quiet = ServerFactory(name="Людно"), ServerFactory(name="Тихо")
    foreign = ServerFactory(name="Hypixel", languages=["en"])
    SnapshotFactory(server=busy, players_online=90)
    SnapshotFactory(server=quiet, players_online=4)
    SnapshotFactory(server=foreign, players_online=900)
    status.store(
        {busy.pk: online(players=90), quiet.pk: online(players=4), foreign.pk: online(players=900)}
    )
    for index in range(8):
        SkinFactory(title=f"Скін {index}", trend_score=index)
    old = SkinFactory(title="Торішній", trend_score=0)
    Skin.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=300))
    PackFactory(title="Техно", trend_score=4)
    PackFactory(title="Тиша")
    PackFactory(title="Форджева", loader="forge", trend_score=9)
    PackFactory(title="Стара", game_version="1.20.1", trend_score=8)


def test_guests_without_my_game_get_popular_and_the_common_blocks(api_client, content):
    body = api_client.get("/api/v1/home").json()

    assert body["for_you"]["basis"] == "popular"
    assert [m["slug"] for m in body["for_you"]["mods"]] == [
        "forge-only",
        "old",
        "sodium",
        "faithful",
    ]
    assert [p["title"] for p in body["packs"]] == ["Форджева", "Стара", "Техно", "Тиша"]
    # Only Ukrainian-speaking servers, busiest first
    assert [s["name"] for s in body["servers_online"]] == ["Людно", "Тихо"]
    assert body["servers_online"][0]["live"]["players_online"] == 90
    assert body["skin_of_day"] is not None
    assert len(body["skins"]) == 6
    assert body["skin_of_day"]["id"] not in [s["id"] for s in body["skins"]]


def test_guests_with_the_cookie_get_only_what_fits(api_client, content):
    api_client.cookies[GAME_COOKIE] = "26.3:fabric"

    body = api_client.get("/api/v1/home").json()

    assert body["for_you"] == {**body["for_you"], "basis": "profile", "loader": "fabric"}
    assert [m["slug"] for m in body["for_you"]["mods"]] == ["sodium"]
    assert [p["title"] for p in body["packs"]] == ["Техно", "Тиша"]


def test_a_vanilla_game_gets_what_runs_without_a_loader(api_client, content):
    api_client.cookies[GAME_COOKIE] = "26.3:vanilla"

    body = api_client.get("/api/v1/home").json()

    assert [m["slug"] for m in body["for_you"]["mods"]] == ["faithful"]
    # Packs of any loader for the version: a vanilla game has none of its own
    assert [p["title"] for p in body["packs"]] == ["Форджева", "Техно", "Тиша"]


def test_players_get_mods_for_their_version_and_loader(content):
    user = UserFactory()
    GameProfile.objects.filter(user=user).update(game_version="26.3", loader="fabric")

    body = client_for(user).get("/api/v1/home").json()

    assert body["for_you"] == {**body["for_you"], "basis": "profile", "game_version": "26.3"}
    assert [m["slug"] for m in body["for_you"]["mods"]] == ["sodium"]
    assert [p["title"] for p in body["packs"]] == ["Техно", "Тиша"]


def test_skin_of_day_changes_daily_among_the_most_liked(content):
    pool = set(
        Skin.objects.order_by("-trend_score").values_list("pk", flat=True)[
            : selectors.SKIN_OF_DAY_POOL
        ]
    )
    first = selectors.skin_of_day(viewer=None, today=date(2026, 11, 11))
    again = selectors.skin_of_day(viewer=None, today=date(2026, 11, 11))
    next_day = selectors.skin_of_day(viewer=None, today=date(2026, 11, 12))

    assert first.pk == again.pk and first.pk in pool
    assert next_day.pk != first.pk


def test_skin_of_day_holds_when_trends_move(content):
    from django.core.cache import cache

    day = date(2026, 11, 11)
    first = selectors.skin_of_day(viewer=None, today=day)
    # Trends reshuffle within the pool, the cache is rebuilt
    Skin.objects.filter(pk=first.pk).update(trend_score=1000)
    cache.delete(f"home:skin-of-day:{day.isoformat()}")

    assert selectors.skin_of_day(viewer=None, today=day).pk == first.pk


def test_viewer_state_is_personal_even_with_the_cache(content):
    first, second = UserFactory(), UserFactory()
    skin = SkinFactory(title="Найновіший")
    Favorite.objects.create(
        user=first, content_type=get_kind("skin").content_type, object_id=skin.pk
    )

    def newest(client) -> dict:
        body = client.get("/api/v1/home").json()
        # It may be the skin of the day, then it is not repeated in the list
        return next(s for s in [body["skin_of_day"], *body["skins"]] if s["id"] == skin.pk)

    client_for(second).get("/api/v1/home")  # fills the cache
    mine, theirs = newest(client_for(first)), newest(client_for(second))

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
    Favorite.objects.create(
        user=UserFactory(), content_type=get_kind("skin").content_type, object_id=skin.pk
    )
    server = ServerFactory(trend_score=1)
    status.store({server.pk: online(players=12)})

    assert (
        api_client.get("/api/v1/top", {"kind": "skin", "period": "month"}).json()["skins"][0]["id"]
        == skin.pk
    )
    pack = PackFactory(score=4.5)
    packs = api_client.get("/api/v1/top", {"kind": "pack", "period": "all"}).json()["packs"]
    assert [p["slug"] for p in packs] == [pack.slug]
    servers = api_client.get("/api/v1/top", {"kind": "server"}).json()["servers"]
    assert servers[0]["live"]["players_online"] == 12
    assert api_client.get("/api/v1/top", {"period": "year"}).status_code == 400
