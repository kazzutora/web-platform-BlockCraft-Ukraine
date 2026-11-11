import pytest
from rest_framework.test import APIClient

from apps.accounts.models import UserSettings
from apps.accounts.tests.factories import UserFactory
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.servers.tests.factories import ServerFactory
from apps.social import services as social

pytestmark = pytest.mark.django_db


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_login(user)
    return client


def test_first_review_notifies_the_owner_and_updates_do_not():
    server = ServerFactory(owned=True)
    reviewer = UserFactory()

    social.upsert_review(user=reviewer, kind="server", identifier=server.slug, stars=4, text="Ок")
    social.upsert_review(user=reviewer, kind="server", identifier=server.slug, stars=5)

    assert list(Notification.objects.values_list("user", "type")) == [(server.owner_id, "review")]


def test_switched_off_types_are_not_saved():
    user = UserFactory()
    UserSettings.objects.filter(user=user).update(notify_prefs={"review": False})
    user.refresh_from_db()

    notify(user=user, type="review", actor="x")
    notify(user=user, type="warning", reason="x")

    assert list(Notification.objects.values_list("type", flat=True)) == ["warning"]


def test_list_unread_and_mark_read():
    user = UserFactory()
    for n in range(23):
        Notification.objects.create(user=user, type="review", payload={"title": f"Скін {n}"})
    client = client_for(user)

    page = client.get("/api/v1/me/notifications").json()
    assert (page["unread_count"], len(page["results"]), page["next_page"]) == (23, 20, 2)
    assert page["results"][0]["payload"]["title"] == "Скін 22"
    assert client.get("/api/v1/me/notifications/unread").json() == {"unread_count": 23}

    first = page["results"][0]["id"]
    assert client.post("/api/v1/me/notifications/read", {"ids": [first]}, format="json").json() == {
        "unread_count": 22
    }
    assert client.post("/api/v1/me/notifications/read", {}, format="json").json() == {
        "unread_count": 0
    }


def test_notifications_are_private(api_client):
    Notification.objects.create(user=UserFactory(), type="review")

    assert api_client.get("/api/v1/me/notifications").status_code == 401
    assert client_for(UserFactory()).get("/api/v1/me/notifications").json()["results"] == []
