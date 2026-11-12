"""«Збірка за ціллю»: real catalog projects per goal, picked for the game (R8.5)."""

import pytest

from apps.compat.types import Target
from apps.core.exceptions import DomainError
from apps.core.game import GAME_COOKIE
from apps.help import services
from apps.packs.models import Pack
from apps.packs.tests.factories import mod

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("game_versions")]

FABRIC = Target("26.3", "fabric")


def catalog_mod(slug: str, *, loaders=("fabric",), game_versions=("26.3",), **fields):
    """A project whose catalog fields match its only file."""
    project = mod(slug=slug, game_versions=list(game_versions), loaders=list(loaders), **fields)
    project.loaders, project.game_versions = list(loaders), list(game_versions)
    project.save(update_fields=["loaders", "game_versions"])
    return project


def fabric_mod(slug: str, **fields):
    return catalog_mod(slug, **fields)


def picks(found) -> dict[str, str | None]:
    return {choice.slot: choice.slug for choice in found.choices}


def test_each_slot_takes_the_first_candidate_that_fits_and_brings_its_dependencies():
    api = fabric_mod("fabric-api")
    fabric_mod("sodium", requires=[api])
    catalog_mod("embeddium", loaders=["forge"])
    fabric_mod("lithium")

    found = services.preview(goals=["fps"], target=FABRIC)

    assert picks(found)["renderer"] == "sodium"
    assert picks(found)["game_logic"] == "lithium"
    # Not in the catalog: the slot stays empty, no made-up project
    assert picks(found)["memory"] is None
    installed = {item.project.slug: item.reason for item in found.resolved.resolution.items}
    assert installed == {"sodium": "requested", "lithium": "requested", "fabric-api": "dependency"}


def test_another_loader_gets_the_next_candidate():
    fabric_mod("sodium")
    catalog_mod("embeddium", loaders=["forge"])

    found = services.preview(goals=["fps"], target=Target("26.3", "forge"))

    assert picks(found)["renderer"] == "embeddium"


def test_a_pick_without_a_file_for_the_game_gives_way():
    # The project says 26.3, its only file is for 1.21.1
    mod(slug="sodium", game_versions=["1.21.1"], loaders=["fabric"])
    from apps.mods.models import Project

    Project.objects.filter(slug="sodium").update(game_versions=["1.21.1", "26.3"])
    fabric_mod("embeddium")

    found = services.preview(goals=["fps"], target=FABRIC)

    assert picks(found)["renderer"] == "embeddium"


def test_a_conflicting_later_pick_is_dropped():
    lithium = fabric_mod("lithium")
    fabric_mod("sodium", breaks=[lithium])

    found = services.preview(goals=["fps"], target=FABRIC)

    assert picks(found)["renderer"] == "sodium"
    assert picks(found)["game_logic"] is None
    assert found.resolved.resolution.conflicts == []


def test_shared_slots_come_once_and_journeymap_is_also_the_world_map():
    fabric_mod("sodium")
    fabric_mod("journeymap")
    fabric_mod("xaeros-world-map")

    found = services.preview(goals=["fps", "beauty", "maps"], target=FABRIC)

    slots = [choice.slot for choice in found.choices]
    assert slots.count("renderer") == 1
    assert picks(found)["minimap"] == "journeymap"
    assert picks(found)["world_map"] is None


def test_preview_api_uses_my_game_and_needs_a_mod_loader(api_client):
    fabric_mod("xaeros-minimap")
    api_client.cookies[GAME_COOKIE] = "26.3:fabric"

    body = api_client.post("/api/v1/help/goals/preview", {"goals": ["maps"]}, format="json")

    assert body.status_code == 200
    data = body.json()
    assert data["target"] == {"game_version": "26.3", "loader": "fabric"}
    assert {"slot": "minimap", "slug": "xaeros-minimap"} in data["choices"]
    assert [item["project"]["slug"] for item in data["resolution"]["items"]] == ["xaeros-minimap"]

    api_client.cookies[GAME_COOKIE] = "26.3:vanilla"
    refused = api_client.post("/api/v1/help/goals/preview", {"goals": ["maps"]}, format="json")
    assert (refused.status_code, refused.json()["code"]) == (400, "needs_mod_loader")
    unknown = api_client.post("/api/v1/help/goals/preview", {"goals": ["pvp"]}, format="json")
    assert unknown.status_code == 400


def test_players_save_the_preview_as_a_private_draft(api_client, auth_client, user):
    fabric_mod("jei")
    fabric_mod("appleskin")
    request = {"goals": ["inventory"], "game_version": "26.3", "loader": "fabric"}

    assert api_client.post("/api/v1/help/goals/pack", request, format="json").status_code in {
        401,
        403,
    }
    response = auth_client.post("/api/v1/help/goals/pack", request, format="json")

    assert response.status_code == 201
    pack = Pack.objects.get(slug=response.json()["slug"])
    assert (pack.author, pack.visibility, pack.status) == (user, "private", "draft")
    assert pack.title == "Збірка: Інвентар і рецепти"
    assert [item.project.slug for item in pack.items.order_by("position")] == ["jei", "appleskin"]


def test_nothing_to_save_when_nothing_fits(auth_client):
    response = auth_client.post(
        "/api/v1/help/goals/pack",
        {"goals": ["maps"], "game_version": "26.3", "loader": "fabric"},
        format="json",
    )

    assert (response.status_code, response.json()["code"]) == (400, "nothing_fits")


def test_a_conflict_with_an_implicit_engine_drops_the_later_pick():
    sodium = fabric_mod("sodium")
    # Iris comes in by itself for the shader, and refuses this Sodium
    fabric_mod("iris", breaks=[sodium])
    catalog_mod("complementary-reimagined", project_type="shader", loaders=["iris"])

    found = services.preview(goals=["beauty"], target=FABRIC)

    assert picks(found) == {"renderer": "sodium", "shader": None}
    assert found.resolved.resolution.conflicts == []


def test_a_dependency_without_a_file_for_the_game_drops_its_pick():
    old_library = mod(slug="old-lib", game_versions=["1.21.1"], loaders=["fabric"])
    fabric_mod("jei", requires=[old_library])
    fabric_mod("emi")

    found = services.preview(goals=["inventory"], target=FABRIC)

    assert picks(found)["recipes"] == "emi"
    statuses = {item.project.slug: item.status for item in found.resolved.resolution.items}
    assert "old-lib" not in statuses and set(statuses.values()) == {"ok"}


def test_when_every_candidate_fails_the_slot_stays_empty():
    lithium = fabric_mod("lithium")
    fabric_mod("sodium", breaks=[lithium])
    fabric_mod("embeddium", breaks=[lithium])

    found = services.preview(goals=["fps"], target=FABRIC)

    assert picks(found)["renderer"] == "sodium"
    assert picks(found)["game_logic"] is None
    assert found.resolved.resolution.conflicts == []


def test_hidden_projects_are_never_picked_and_versions_must_be_known():
    from apps.mods.models import Project

    fabric_mod("xaeros-minimap")
    fabric_mod("journeymap")
    Project.objects.filter(slug="xaeros-minimap").update(is_hidden=True)

    assert picks(services.preview(goals=["maps"], target=FABRIC))["minimap"] == "journeymap"
    with pytest.raises(DomainError) as error:
        services.preview(goals=["maps"], target=Target("0.1", "fabric"))
    assert error.value.code == "unknown_game_version"


def test_preview_and_save_stay_within_a_query_budget(
    api_client, auth_client, django_assert_max_num_queries
):
    api = fabric_mod("fabric-api")
    for slug in ("sodium", "lithium", "ferrite-core", "entityculling"):
        fabric_mod(slug, requires=[api])
    body = {"goals": ["fps"], "game_version": "26.3", "loader": "fabric"}

    with django_assert_max_num_queries(25):
        assert api_client.post("/api/v1/help/goals/preview", body, format="json").status_code == 200
    auth_client.cookies[GAME_COOKIE] = "26.3:fabric"
    with django_assert_max_num_queries(60):
        saved = auth_client.post("/api/v1/help/goals/pack", {"goals": ["fps"]}, format="json")
    # The game came from the player's «Моя гра» cookie, not from the request
    assert Pack.objects.get(slug=saved.json()["slug"]).game_version == "26.3"
