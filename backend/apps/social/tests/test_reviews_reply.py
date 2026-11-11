import pytest
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.notifications.models import Notification
from apps.packs.tests.factories import PackFactory
from apps.servers.tests.factories import ServerFactory
from apps.social import services

pytestmark = pytest.mark.django_db


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_login(user)
    return client


def review_of(kind: str, identifier: str, player=None):
    player = player or UserFactory()
    review, _ = services.upsert_review(
        user=player, kind=kind, identifier=identifier, stars=4, text="Добре"
    )
    return review


def test_pack_author_is_told_and_answers_once_the_reviewer_hears():
    pack = PackFactory()
    review = review_of("pack", pack.slug)
    assert Notification.objects.get(user=pack.author).type == "review_on_your_pack"

    response = client_for(pack.author).put(
        f"/api/v1/reviews/{review.pk}/reply", {"text": "Дякую!"}, format="json"
    )
    client_for(pack.author).put(
        f"/api/v1/reviews/{review.pk}/reply", {"text": "Дякую ще раз!"}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["reply_by"]["nickname"] == pack.author.nickname
    assert Notification.objects.filter(user=review.user, type="review_reply").count() == 1


def test_proven_server_owner_answers_others_cannot():
    owner = UserFactory()
    server = ServerFactory(owner=owner, is_verified=True)
    review = review_of("server", server.slug)

    stranger = client_for(UserFactory()).put(
        f"/api/v1/reviews/{review.pk}/reply", {"text": "Я тут головний"}, format="json"
    )
    mine = client_for(owner).put(
        f"/api/v1/reviews/{review.pk}/reply", {"text": "Чекаємо!"}, format="json"
    )

    assert (stranger.status_code, mine.status_code) == (403, 200)
    assert Notification.objects.get(user=owner).type == "review_on_your_server"


def test_nobody_answers_for_a_modrinth_modpack():
    pack = PackFactory(origin="modrinth")
    review = review_of("pack", pack.slug)

    response = client_for(pack.author).put(
        f"/api/v1/reviews/{review.pk}/reply", {"text": "?"}, format="json"
    )

    assert response.status_code == 403
    assert not Notification.objects.filter(type="review_on_your_pack").exists()


def test_reviews_page_says_who_may_answer():
    pack = PackFactory()
    review_of("pack", pack.slug)

    mine = client_for(pack.author).get("/api/v1/reviews", {"kind": "pack", "id": pack.slug})
    guest = APIClient().get("/api/v1/reviews", {"kind": "pack", "id": pack.slug})

    assert mine.json()["results"][0]["can_reply"] is True
    assert guest.json()["results"][0]["can_reply"] is False


def test_empty_answer_removes_it():
    pack = PackFactory()
    review = review_of("pack", pack.slug)
    services.reply_to_review(review=review, user=pack.author, text="Дякую")

    services.reply_to_review(review=review, user=pack.author, text="  ")

    review.refresh_from_db()
    assert (review.reply_text, review.reply_by) == ("", None)
