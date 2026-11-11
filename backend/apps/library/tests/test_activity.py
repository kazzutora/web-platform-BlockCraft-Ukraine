import pytest
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.library.tests.factories import CollectionFactory
from apps.mods.tests.factories import ProjectFactory, VersionFactory
from apps.packs.tests.factories import PackFactory
from apps.servers.tests.factories import ServerFactory
from apps.skins.tests.factories import SkinFactory
from apps.social import services as social

pytestmark = pytest.mark.django_db


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_login(user)
    return client


def test_took_lists_what_the_player_took_across_kinds(django_assert_max_num_queries):
    player = UserFactory()
    client = client_for(player)
    project = ProjectFactory(slug="sodium")
    VersionFactory(project=project, game_versions=["1.21.1"], loaders=["fabric"])
    client.get("/api/v1/mods/sodium/download", {"game_version": "1.21.1", "loader": "fabric"})
    server = ServerFactory()
    client.post(f"/api/v1/servers/{server.slug}/copy-ip")
    skin = SkinFactory(title="Мавка")
    client.get(f"/api/v1/skins/{skin.pk}/download")

    with django_assert_max_num_queries(12):
        data = client.get("/api/v1/me/activity", {"section": "took"}).json()

    assert [(row["kind"], row["action"]) for row in data["results"]] == [
        ("skin", "download_png"),
        ("server", "copy_ip"),
        ("mod", "download"),
    ]
    assert data["count"] == 3


def test_guests_take_without_a_trace(api_client):
    skin = SkinFactory()

    api_client.get(f"/api/v1/skins/{skin.pk}/download")

    from apps.library.models import Download

    assert not Download.objects.exists()


def test_shared_counts_and_lists_everything_the_player_gave():
    player = UserFactory(nickname="Mavka")
    PackFactory(author=player, title="Друзі")
    PackFactory(author=player, title="Чернетка", status="draft")
    CollectionFactory(owner=player, items_count=2, title="Найкраще")
    ServerFactory(owner=player, is_verified=True)
    SkinFactory(added_by=player)
    project = ProjectFactory(slug="iris")
    social.upsert_review(user=player, kind="mod", identifier=project.slug, stars=5, text="Топ")

    mine = client_for(player).get("/api/v1/me/activity", {"section": "shared"}).json()
    public = APIClient().get("/api/v1/users/Mavka/shared").json()

    assert mine["counts"] == {
        "packs": 2,
        "collections": 1,
        "reviews": 1,
        "translations": 0,
        "servers": 1,
        "skins": 1,
    }
    assert public["counts"]["packs"] == 1  # the draft is mine only
    assert {row["type"] for row in public["results"]} == {
        "pack",
        "collection",
        "review",
        "server",
        "skin",
    }


def test_private_profile_shares_nothing_with_others():
    player = UserFactory(nickname="Tihyi", is_private=True)
    PackFactory(author=player)

    data = APIClient().get("/api/v1/users/Tihyi/shared").json()

    assert (data["count"], data["results"]) == (0, [])


def test_activity_needs_sign_in(api_client):
    assert api_client.get("/api/v1/me/activity").status_code == 401


def test_public_shared_hides_reviews_of_what_guests_cannot_open():
    player = UserFactory(nickname="Rev")
    secret = PackFactory(title="SecretPack")
    social.upsert_review(user=player, kind="pack", identifier=secret.slug, stars=4)
    secret.visibility = "link"
    secret.save()
    hidden = ProjectFactory(slug="hidden-mod")
    social.upsert_review(user=player, kind="mod", identifier=hidden.slug, stars=2)
    hidden.is_hidden = True
    hidden.save()

    public = APIClient().get("/api/v1/users/Rev/shared").json()
    mine = client_for(player).get("/api/v1/me/activity", {"section": "shared"}).json()

    assert public["results"] == []
    assert len(mine["results"]) == 2


def test_shared_page_must_be_a_number():
    UserFactory(nickname="P2")

    assert APIClient().get("/api/v1/users/P2/shared", {"page": "abc"}).status_code == 400


def test_shared_has_no_n_plus_one(django_assert_max_num_queries):
    player = UserFactory(nickname="Many")
    for _ in range(5):
        PackFactory(author=player)
        CollectionFactory(owner=player, items_count=1)
        SkinFactory(added_by=player)
        project = ProjectFactory()
        social.upsert_review(user=player, kind="mod", identifier=project.slug, stars=5)

    with django_assert_max_num_queries(20):
        data = APIClient().get("/api/v1/users/Many/shared").json()
    assert data["count"] == 20
