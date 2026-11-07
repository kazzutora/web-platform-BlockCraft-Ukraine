import pytest

from apps.library.models import Collection
from apps.library.tests.factories import CollectionFactory
from apps.mods.tests.factories import CategoryFactory, ProjectFactory
from apps.social import services

pytestmark = pytest.mark.django_db


def test_saves_score_for_collections(user):
    collection = CollectionFactory(visibility=Collection.Visibility.PUBLIC, favorites_count=3)

    services.recalc_scores()

    collection.refresh_from_db()
    assert collection.score == 3


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
