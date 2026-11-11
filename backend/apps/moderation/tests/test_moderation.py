from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.core.kinds import get_kind
from apps.library.models import Collection
from apps.library.tests.factories import CollectionFactory
from apps.moderation import services
from apps.moderation.models import Report, Sanction
from apps.moderation.tasks import lift_expired_bans
from apps.notifications.models import Notification
from apps.packs.tests.factories import PackFactory
from apps.servers.tests.factories import ServerFactory
from apps.skins.tests.factories import SkinFactory

pytestmark = pytest.mark.django_db


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_login(user)
    return client


def report(user, kind, identifier, reason="inappropriate"):
    return client_for(user).post(
        "/api/v1/reports", {"kind": kind, "id": identifier, "reason": reason}, format="json"
    )


# Reports


def test_report_goes_to_the_queue():
    skin = SkinFactory()

    response = report(UserFactory(), "skin", skin.pk)

    assert response.status_code == 201
    assert Report.objects.get().status == Report.Status.NEW


def test_one_open_report_per_player_and_no_reports_on_own_work():
    skin = SkinFactory()
    player = UserFactory()
    report(player, "skin", skin.pk)

    assert report(player, "skin", skin.pk).json()["code"] == "already_reported"
    pack = PackFactory()
    assert report(pack.author, "pack", pack.slug).json()["code"] == "own_object"


def test_five_independent_reports_hide_the_object(api_client):
    skin = SkinFactory()
    for _ in range(4):
        report(UserFactory(), "skin", skin.pk)
    skin.refresh_from_db()
    assert not skin.is_hidden

    report(UserFactory(), "skin", skin.pk, reason="stolen")

    skin.refresh_from_db()
    assert skin.is_hidden
    assert api_client.get(f"/api/v1/skins/{skin.pk}").status_code == 404
    assert Report.objects.filter(auto_hidden=True).count() == 5


def test_private_collection_cannot_be_reported():
    private = CollectionFactory(visibility="private")

    assert report(UserFactory(), "collection", private.pk).status_code == 404


def test_reports_are_rate_limited():
    player = UserFactory()
    skins = SkinFactory.create_batch(21)

    statuses = [report(player, "skin", skin.pk).status_code for skin in skins]

    assert statuses[:20] == [201] * 20
    assert statuses[20] == 429


def test_accepting_reports_hides_and_notifies_the_author():
    pack = PackFactory(title="Сумнівний")
    report(UserFactory(), "pack", pack.slug)

    services.accept_reports(reports=Report.objects.all(), moderator=UserFactory())

    pack.refresh_from_db()
    assert pack.status == pack.Status.HIDDEN
    assert Report.objects.get().status == Report.Status.ACCEPTED
    note = Notification.objects.get(user=pack.author)
    assert (note.type, note.payload["title"]) == ("hidden", "Сумнівний")


def test_rejecting_reports_brings_an_auto_hidden_object_back():
    collection = CollectionFactory(items_count=2)
    for _ in range(5):
        report(UserFactory(), "collection", collection.pk)
    collection.refresh_from_db()
    assert collection.visibility == Collection.Visibility.PRIVATE

    services.reject_reports(reports=Report.objects.all(), moderator=None)

    collection.refresh_from_db()
    assert collection.visibility == Collection.Visibility.PUBLIC
    assert Notification.objects.get(user=collection.owner).type == "restored"
    assert set(Report.objects.values_list("status", flat=True)) == {"rejected"}


def test_admin_report_queue_accepts(admin_client):
    skin = SkinFactory()
    report(UserFactory(), "skin", skin.pk)

    admin_client.post(
        reverse("admin:moderation_report_changelist"),
        {"action": "accept", "_selected_action": list(Report.objects.values_list("pk", flat=True))},
    )

    skin.refresh_from_db()
    assert skin.is_hidden


# Sanctions


def test_publish_ban_blocks_reviews():
    player = UserFactory()
    server = ServerFactory()
    services.issue_sanction(user=player, type=Sanction.Type.PUBLISH_BAN, reason="Спам")
    client = client_for(player)

    review = client.put(
        "/api/v1/reviews", {"kind": "server", "id": server.slug, "stars": 5}, format="json"
    )

    assert (review.status_code, review.json()["code"]) == (403, "publish_banned")
    assert Notification.objects.get(user=player).type == "warning"


def test_ban_signs_the_player_out_until_it_expires():
    player = UserFactory()
    client = client_for(player)
    services.issue_sanction(
        user=player,
        type=Sanction.Type.BAN,
        reason="Образи",
        until=timezone.now() + timedelta(days=1),
    )

    assert client.get("/api/v1/me").status_code == 401

    Sanction.objects.update(until=timezone.now() - timedelta(minutes=1))
    assert lift_expired_bans.delay().get() == 1
    player.refresh_from_db()
    assert player.is_active is True


def test_expired_publish_ban_no_longer_applies():
    player = UserFactory()
    Sanction.objects.create(
        user=player,
        type=Sanction.Type.PUBLISH_BAN,
        reason="Минуло",
        until=timezone.now() - timedelta(days=1),
    )

    services.ensure_can_publish(player)


# Profanity in user content


def test_banned_word_in_a_review_is_blocked_with_an_explanation():
    server = ServerFactory()

    response = client_for(UserFactory()).put(
        "/api/v1/reviews",
        {"kind": "server", "id": server.slug, "stars": 1, "text": "адмін — мудак"},
        format="json",
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "banned_word"
    assert body["fields"]["text"] == [
        "Текст містить слово, яке в нас заборонене. Переформулюй, будь ласка."
    ]


def test_banned_words_in_bio_and_titles(auth_client):
    assert auth_client.patch("/api/v1/me", {"bio": "пи3да"}, format="json").status_code == 400
    response = auth_client.post("/api/v1/collections", {"title": "fuck this"}, format="json")
    assert response.json()["fields"] == {"title": [response.json()["detail"]]}


def test_kind_names_are_stable():
    assert get_kind("skin").name == "skin"
