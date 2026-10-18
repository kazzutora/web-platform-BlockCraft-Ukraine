import pytest

from apps.library.models import Collection, Favorite
from apps.mods.models import Project
from apps.mods.tests.factories import ProjectFactory

from .factories import CollectionFactory

pytestmark = pytest.mark.django_db


def favorite(client, kind="mod", identifier="sodium", method="post"):
    if method == "delete":
        return client.delete(f"/api/v1/favorites?kind={kind}&id={identifier}")
    return client.post("/api/v1/favorites", {"kind": kind, "id": identifier}, format="json")


def test_save_and_unsave_a_mod_keeps_the_counter_right(auth_client):
    project = ProjectFactory(slug="sodium")

    first = favorite(auth_client)
    again = favorite(auth_client)

    assert first.status_code == again.status_code == 200
    assert again.json() == {"kind": "mod", "id": "sodium", "favorited": True, "favorites_count": 1}
    assert Favorite.objects.count() == 1

    removed = favorite(auth_client, method="delete")
    favorite(auth_client, method="delete")

    assert removed.json()["favorited"] is False
    project.refresh_from_db()
    assert project.favorites_count == 0


def test_favorites_need_sign_in(api_client):
    ProjectFactory(slug="sodium")

    assert favorite(api_client).status_code == 401


def test_unknown_kind_and_hidden_targets(auth_client):
    ProjectFactory(slug="waiting", status=Project.Status.PENDING)

    unknown = favorite(auth_client, kind="planet")
    assert unknown.status_code == 400
    assert "kind" in unknown.json()["fields"]
    assert favorite(auth_client, identifier="waiting").status_code == 404


def test_private_collection_of_someone_else_cannot_be_saved(auth_client):
    collection = CollectionFactory(visibility=Collection.Visibility.PRIVATE)

    assert favorite(auth_client, kind="collection", identifier=collection.pk).status_code == 404


def test_saved_lists_one_kind_newest_first_with_version_filter(auth_client, user):
    old = ProjectFactory(slug="old", game_versions=["1.20.1"])
    new = ProjectFactory(slug="new", game_versions=["26.3"])
    ProjectFactory(slug="not-saved")
    for project in (old, new):
        favorite(auth_client, identifier=project.slug)
    collection = CollectionFactory()
    favorite(auth_client, kind="collection", identifier=collection.pk)

    mods = auth_client.get("/api/v1/me/saved", {"kind": "mod"}).json()
    assert [item["id"] for item in mods["results"]] == ["new", "old"]
    assert mods["results"][0]["mod"]["is_favorited"] is True
    assert mods["results"][0]["collection"] is None

    filtered = auth_client.get("/api/v1/me/saved", {"kind": "mod", "game_version": "26.3"}).json()
    assert [item["id"] for item in filtered["results"]] == ["new"]

    collections = auth_client.get("/api/v1/me/saved", {"kind": "collection"}).json()
    assert collections["results"][0]["collection"]["id"] == collection.pk


def test_saved_skips_projects_that_were_hidden(auth_client):
    project = ProjectFactory(slug="sodium")
    favorite(auth_client)
    Project.objects.filter(pk=project.pk).update(status=Project.Status.HIDDEN)

    assert auth_client.get("/api/v1/me/saved").json()["count"] == 0
