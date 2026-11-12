"""Crash log: the browser sends mod ids and names, we answer what is in the catalog."""

import pytest

from apps.mods.tests.factories import ProjectFactory
from apps.packs.models import LoaderRelease

pytestmark = pytest.mark.django_db

URL = "/api/v1/help/crash"


def test_mods_are_matched_by_slug_dashes_alias_or_title(api_client, django_assert_max_num_queries):
    ProjectFactory(slug="sodium", title="Sodium")
    ProjectFactory(slug="fabric-api", title="Fabric API")
    ProjectFactory(slug="a-good-place", title="A Good Place")
    ProjectFactory(slug="xaeros-minimap", title="Xaero's Minimap")
    hidden = ProjectFactory(slug="seatify", title="Seatify", is_hidden=True)
    mods = [
        {"id": "sodium", "name": "Sodium"},
        {"id": "fabric"},  # Fabric API's old mod id
        {"id": "a_good_place", "name": "A Good Place"},
        {"id": "xaerominimap", "name": "Xaero's Minimap"},
        {"id": hidden.slug},
        {"id": "touhou_little_maid"},
        {"id": "minecraft"},
        {"id": "neoforge"},
    ]

    with django_assert_max_num_queries(6):
        body = api_client.post(URL, {"mods": mods}, format="json").json()

    found = {row["id"]: row["project"]["slug"] if row["project"] else None for row in body["mods"]}
    assert found == {
        "sodium": "sodium",
        "fabric": "fabric-api",
        "a_good_place": "a-good-place",
        "xaerominimap": "xaeros-minimap",
        "seatify": None,  # hidden by a moderator
        "touhou_little_maid": None,
    }
    assert body["loader_release"] is None


def test_the_latest_loader_for_the_game_of_the_log(api_client):
    LoaderRelease.objects.create(loader="neoforge", game_version="1.21.1", version="21.1.230")

    body = api_client.post(
        URL,
        {"mods": [{"id": "sepals"}], "loader": "neoforge", "game_version": "1.21.1"},
        format="json",
    ).json()

    assert body["loader_release"] == {
        "loader": "neoforge",
        "game_version": "1.21.1",
        "version": "21.1.230",
    }


def test_the_request_is_bounded(api_client):
    too_many = {"mods": [{"id": f"mod{n}"} for n in range(101)]}

    assert api_client.post(URL, too_many, format="json").status_code == 400
    assert api_client.post(URL, {"mods": [{"id": "x" * 65}]}, format="json").status_code == 400
