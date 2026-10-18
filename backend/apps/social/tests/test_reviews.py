import pytest
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.mods.models import Project
from apps.mods.tests.factories import ProjectFactory
from apps.social import services
from apps.social.models import Review

pytestmark = pytest.mark.django_db


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_login(user)
    return client


def review(client, stars, text="", slug="sodium"):
    return client.put(
        "/api/v1/reviews", {"kind": "mod", "id": slug, "stars": stars, "text": text}, format="json"
    )


def test_one_review_per_player_second_one_updates(auth_client):
    project = ProjectFactory(slug="sodium")

    created = review(auth_client, 5, "Чудово")
    updated = review(auth_client, 3, "Вже не так")

    assert created.status_code == 201
    assert updated.status_code == 200
    assert Review.objects.count() == 1
    project.refresh_from_db()
    assert (project.rating_avg, project.rating_count) == (3.0, 1)


def test_rating_counts_every_player(api_client):
    project = ProjectFactory(slug="sodium")
    for stars in (5, 4, 4, 1):
        review(client_for(UserFactory()), stars)

    data = api_client.get("/api/v1/reviews", {"kind": "mod", "id": "sodium"}).json()

    project.refresh_from_db()
    assert (project.rating_avg, project.rating_count) == (3.5, 4)
    assert data["summary"]["distribution"] == {"1": 1, "2": 0, "3": 0, "4": 2, "5": 1}
    assert data["count"] == 4
    assert data["summary"]["my_review"] is None


def test_stars_must_be_1_to_5(auth_client):
    ProjectFactory(slug="sodium")

    for stars in (0, 6):
        assert review(auth_client, stars).status_code == 400


def test_collections_cannot_be_reviewed(auth_client, user):
    from apps.library.tests.factories import CollectionFactory

    collection = CollectionFactory(owner=user)
    response = auth_client.put(
        "/api/v1/reviews", {"kind": "collection", "id": collection.pk, "stars": 5}, format="json"
    )

    assert response.status_code == 400
    assert response.json()["code"] == "action_not_allowed"


def test_helpful_votes_sort_and_cannot_vote_own(api_client):
    ProjectFactory(slug="sodium")
    author_a, author_b = UserFactory(), UserFactory()
    review(client_for(author_a), 5, "Перший")
    review(client_for(author_b), 4, "Другий")
    second = Review.objects.get(user=author_b)
    voter = client_for(UserFactory())

    vote = voter.post(f"/api/v1/reviews/{second.pk}/vote", {"is_helpful": True}, format="json")
    own = client_for(author_b).post(
        f"/api/v1/reviews/{second.pk}/vote", {"is_helpful": True}, format="json"
    )

    assert vote.json()["helpful_count"] == 1
    assert vote.json()["my_vote"] is True
    assert own.status_code == 400
    helpful = api_client.get("/api/v1/reviews", {"kind": "mod", "id": "sodium"}).json()
    assert [item["text"] for item in helpful["results"]] == ["Другий", "Перший"]


def test_author_or_moderator_deletes_and_rating_follows(auth_client, user):
    project = ProjectFactory(slug="sodium")
    review(auth_client, 4)
    mine = Review.objects.get()

    stranger = client_for(UserFactory())
    assert stranger.delete(f"/api/v1/reviews/{mine.pk}").status_code == 403
    assert auth_client.delete(f"/api/v1/reviews/{mine.pk}").status_code == 204

    project.refresh_from_db()
    assert (project.rating_avg, project.rating_count) == (0, 0)


def test_bayesian_score_pulls_small_samples_to_the_mean():
    popular = ProjectFactory(slug="popular")
    lucky = ProjectFactory(slug="lucky")
    for _ in range(20):
        services.upsert_review(user=UserFactory(), kind="mod", identifier="popular", stars=4)
    services.upsert_review(user=UserFactory(), kind="mod", identifier="lucky", stars=5)

    services.recalc_scores()

    popular.refresh_from_db()
    lucky.refresh_from_db()
    mean = (20 * 4 + 5) / 21
    assert lucky.score == pytest.approx((10 * mean + 5) / 11)
    assert popular.score == pytest.approx((10 * mean + 80) / 30)
    assert popular.score > lucky.score - 0.2  # one 5★ does not jump far above twenty 4★
    unrated = ProjectFactory(slug="unrated")
    services.recalc_scores()
    unrated.refresh_from_db()
    assert unrated.score == pytest.approx(mean)


def test_reviews_of_hidden_projects_are_404(api_client):
    ProjectFactory(slug="hidden", status=Project.Status.HIDDEN)

    assert api_client.get("/api/v1/reviews", {"kind": "mod", "id": "hidden"}).status_code == 404
