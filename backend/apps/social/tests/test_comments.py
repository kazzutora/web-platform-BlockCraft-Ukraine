import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User, UserSettings
from apps.accounts.tests.factories import UserFactory
from apps.library.tests.factories import CollectionFactory
from apps.mods.tests.factories import ProjectFactory
from apps.social.models import Comment

pytestmark = pytest.mark.django_db


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_login(user)
    return client


def post(client, body, parent=None, kind="mod", identifier="sodium"):
    payload = {"kind": kind, "id": identifier, "body": body}
    if parent:
        payload["parent"] = parent
    return client.post("/api/v1/comments", payload, format="json")


def listing(client, kind="mod", identifier="sodium", **params):
    return client.get("/api/v1/comments", {"kind": kind, "id": identifier, **params}).json()


def test_comment_and_reply_one_level_deep(auth_client, api_client):
    project = ProjectFactory(slug="sodium")

    top = post(auth_client, "Як налаштувати?").json()
    reply = post(auth_client, "Ось так", parent=top["id"]).json()
    nested = post(auth_client, "Глибше", parent=reply["id"])

    assert nested.status_code == 400
    assert nested.json()["code"] == "invalid_parent"
    data = listing(api_client)
    assert [c["body"] for c in data["results"]] == ["Як налаштувати?"]
    assert [r["body"] for r in data["results"][0]["replies"]] == ["Ось так"]
    project.refresh_from_db()
    assert project.comments_count == 2
    assert data["comments_count"] == 2
    assert data["can_comment"] is False  # guest


def test_guests_cannot_comment(api_client):
    ProjectFactory(slug="sodium")

    assert post(api_client, "Привіт").status_code == 401


def test_empty_or_long_comments_are_rejected(auth_client):
    ProjectFactory(slug="sodium")

    assert post(auth_client, "   ").status_code == 400
    assert post(auth_client, "x" * 1001).status_code == 400


@pytest.mark.parametrize(
    ("policy", "allowed"),
    [
        (UserSettings.CommentPolicy.ALL, True),
        (UserSettings.CommentPolicy.FOLLOWERS, False),
        (UserSettings.CommentPolicy.NOBODY, False),
    ],
)
def test_owner_decides_who_can_comment(policy, allowed):
    owner = UserFactory()
    UserSettings.objects.filter(user=owner).update(who_can_comment=policy)
    collection = CollectionFactory(owner=owner)
    stranger = client_for(UserFactory())

    response = post(stranger, "Круто", kind="collection", identifier=collection.pk)

    assert (response.status_code == 201) is allowed
    assert listing(stranger, kind="collection", identifier=collection.pk)["can_comment"] is allowed
    assert (
        post(client_for(owner), "Дякую", kind="collection", identifier=collection.pk).status_code
        == 201
    )


def test_owner_pins_one_comment_at_a_time():
    owner = UserFactory()
    collection = CollectionFactory(owner=owner)
    owner_client = client_for(owner)
    first = post(owner_client, "Перший", kind="collection", identifier=collection.pk).json()
    second = post(owner_client, "Другий", kind="collection", identifier=collection.pk).json()
    stranger = client_for(UserFactory())

    assert stranger.post(f"/api/v1/comments/{first['id']}/pin").status_code == 403
    owner_client.post(f"/api/v1/comments/{first['id']}/pin")
    owner_client.post(f"/api/v1/comments/{second['id']}/pin")

    data = listing(stranger, kind="collection", identifier=collection.pk)
    assert [c["body"] for c in data["pinned"]] == ["Другий"]
    assert [c["body"] for c in data["results"]] == ["Перший"]
    assert Comment.objects.filter(is_pinned=True).count() == 1


def test_edit_only_own_comment(auth_client):
    ProjectFactory(slug="sodium")
    comment = post(auth_client, "Помилка").json()

    stranger = client_for(UserFactory())
    assert (
        stranger.patch(
            f"/api/v1/comments/{comment['id']}", {"body": "x"}, format="json"
        ).status_code
        == 403
    )
    edited = auth_client.patch(
        f"/api/v1/comments/{comment['id']}", {"body": "Виправлено"}, format="json"
    )
    assert edited.json()["body"] == "Виправлено"


def test_delete_with_replies_keeps_a_placeholder(auth_client):
    project = ProjectFactory(slug="sodium")
    top = post(auth_client, "Питання").json()
    post(client_for(UserFactory()), "Відповідь", parent=top["id"])

    assert auth_client.delete(f"/api/v1/comments/{top['id']}").status_code == 204

    data = listing(auth_client)
    assert data["results"][0]["is_deleted"] is True
    assert data["results"][0]["body"] == ""
    assert data["results"][0]["replies"][0]["body"] == "Відповідь"
    project.refresh_from_db()
    assert project.comments_count == 1


def test_delete_without_replies_removes_it(auth_client):
    ProjectFactory(slug="sodium")
    comment = post(auth_client, "Нічого").json()

    auth_client.delete(f"/api/v1/comments/{comment['id']}")

    assert not Comment.objects.exists()


def test_moderator_can_delete_any_comment(auth_client):
    ProjectFactory(slug="sodium")
    comment = post(auth_client, "Спам").json()
    moderator = client_for(UserFactory(role=User.Role.MODERATOR))

    assert moderator.delete(f"/api/v1/comments/{comment['id']}").status_code == 204


def test_cursor_pagination(auth_client, settings):
    ProjectFactory(slug="sodium")
    for index in range(23):
        post(auth_client, f"Коментар {index}")

    first = listing(auth_client)
    second = listing(auth_client, cursor=first["next_cursor"])

    assert len(first["results"]) == 20
    assert len(second["results"]) == 3
    assert second["next_cursor"] is None
    assert first["results"][0]["body"] == "Коментар 22"


def test_comments_list_has_no_n_plus_one(api_client, django_assert_max_num_queries):
    ProjectFactory(slug="sodium")
    for _ in range(5):
        author = client_for(UserFactory())
        top = post(author, "Тема").json()
        post(author, "Відповідь", parent=top["id"])

    with django_assert_max_num_queries(8):
        data = listing(api_client)
    assert len(data["results"]) == 5
