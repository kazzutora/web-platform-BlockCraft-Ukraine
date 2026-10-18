import pytest

from apps.library.models import Collection
from apps.library.tests.factories import CollectionFactory
from apps.mods.tests.factories import CategoryFactory, ProjectFactory
from apps.social import services

pytestmark = pytest.mark.django_db


def like(client, collection, method="post"):
    if method == "delete":
        return client.delete(f"/api/v1/likes?kind=collection&id={collection.pk}")
    return client.post("/api/v1/likes", {"kind": "collection", "id": collection.pk}, format="json")


def test_like_and_unlike_a_collection(auth_client):
    collection = CollectionFactory()

    like(auth_client, collection)
    state = like(auth_client, collection).json()
    assert state == {
        "kind": "collection",
        "id": str(collection.pk),
        "liked": True,
        "likes_count": 1,
    }

    state = like(auth_client, collection, method="delete").json()
    assert (state["liked"], state["likes_count"]) == (False, 0)


def test_mods_are_not_liked_but_reviewed(auth_client):
    ProjectFactory(slug="sodium")

    response = auth_client.post("/api/v1/likes", {"kind": "mod", "id": "sodium"}, format="json")

    assert response.status_code == 400


def test_like_score_for_collections(user):
    collection = CollectionFactory(visibility=Collection.Visibility.PUBLIC)
    services.like(user=user, kind="collection", identifier=str(collection.pk))

    services.recalc_scores()

    collection.refresh_from_db()
    assert collection.score == 1


def test_catalog_shows_the_viewer_state(auth_client, user, api_client):
    ProjectFactory(slug="saved")
    ProjectFactory(slug="reviewed")
    auth_client.post("/api/v1/favorites", {"kind": "mod", "id": "saved"}, format="json")
    services.upsert_review(user=user, kind="mod", identifier="reviewed", stars=4)

    mine = {p["slug"]: p for p in auth_client.get("/api/v1/mods").json()["results"]}
    guest = {p["slug"]: p for p in api_client.get("/api/v1/mods").json()["results"]}

    assert (mine["saved"]["is_favorited"], mine["saved"]["my_review_stars"]) == (True, None)
    assert (mine["reviewed"]["is_favorited"], mine["reviewed"]["my_review_stars"]) == (False, 4)
    assert guest["saved"]["is_favorited"] is False
    assert auth_client.get("/api/v1/mods/saved").json()["is_favorited"] is True


def test_viewer_state_adds_no_queries_per_card(auth_client, django_assert_max_num_queries):
    category = CategoryFactory()
    for _ in range(12):
        ProjectFactory(categories=[category])

    # session + user, count, page, categories prefetch
    with django_assert_max_num_queries(5):
        response = auth_client.get("/api/v1/mods")
    assert len(response.json()["results"]) == 12
