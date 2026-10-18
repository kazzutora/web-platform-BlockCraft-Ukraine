import pytest
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.mods.tests.factories import ProjectFactory

pytestmark = pytest.mark.django_db


def test_guests_share_a_cached_catalog_page(django_assert_num_queries):
    ProjectFactory(title="Sodium")
    guest = APIClient()
    guest.get("/api/v1/mods")

    with django_assert_num_queries(0):
        body = guest.get("/api/v1/mods").json()

    assert body["results"][0]["title"] == "Sodium"


def test_other_filters_and_players_are_not_served_from_the_guest_cache():
    ProjectFactory(title="Sodium", project_type="mod")
    APIClient().get("/api/v1/mods")
    ProjectFactory(title="Iris", project_type="shader")

    assert APIClient().get("/api/v1/mods", {"type": "shader"}).json()["count"] == 1
    player = APIClient()
    player.force_login(UserFactory())
    assert player.get("/api/v1/mods").json()["count"] == 2  # fresh: the shader is there
    assert APIClient().get("/api/v1/mods").json()["count"] == 1  # the cached guest page
