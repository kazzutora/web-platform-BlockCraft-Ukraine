import pytest
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.library.models import Collection, CollectionItem
from apps.mods.tests.factories import ProjectFactory

from .factories import CollectionFactory

pytestmark = pytest.mark.django_db

Visibility = Collection.Visibility


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_login(user)
    return client


def add(client, collection, slug, **extra):
    return client.post(
        f"/api/v1/collections/{collection.pk}/items",
        {"kind": "mod", "id": slug, **extra},
        format="json",
    )


def test_create_collection_is_private_by_default(auth_client, user):
    response = auth_client.post("/api/v1/collections", {"title": "Мій сетап"}, format="json")

    assert response.status_code == 201
    data = response.json()
    assert data["visibility"] == "private"
    assert data["can_edit"] is True
    assert data["share_token"]
    assert Collection.objects.get().owner == user


@pytest.mark.parametrize(
    ("visibility", "token", "expected"),
    [
        (Visibility.PUBLIC, "", 200),
        (Visibility.LINK, "", 404),
        (Visibility.LINK, "wrong", 404),
        (Visibility.LINK, "right", 200),
        (Visibility.PRIVATE, "right", 404),
    ],
)
def test_who_can_open_a_collection(api_client, visibility, token, expected):
    collection = CollectionFactory(visibility=visibility, share_token="right")

    response = api_client.get(f"/api/v1/collections/{collection.pk}", {"share_token": token})

    assert response.status_code == expected
    if expected == 200:
        assert response.json()["share_token"] is None  # only editors see it


def test_owner_and_editors_open_private_collections():
    owner, editor = UserFactory(), UserFactory()
    collection = CollectionFactory(owner=owner, visibility=Visibility.PRIVATE)
    collection.editors.add(editor)

    for user in (owner, editor):
        response = client_for(user).get(f"/api/v1/collections/{collection.pk}")
        assert response.status_code == 200
        assert response.json()["can_edit"] is True


def test_items_are_added_once_counted_and_removed():
    owner = UserFactory()
    collection = CollectionFactory(owner=owner)
    ProjectFactory(slug="sodium")
    ProjectFactory(slug="lithium")
    client = client_for(owner)

    add(client, collection, "sodium", note="Для FPS")
    add(client, collection, "sodium")
    response = add(client, collection, "lithium")

    items = response.json()["items"]
    assert [item["target_id"] for item in items] == ["sodium", "lithium"]
    assert items[0]["note"] == "Для FPS"
    assert items[0]["mod"]["slug"] == "sodium"
    collection.refresh_from_db()
    assert collection.items_count == 2

    client.delete(f"/api/v1/collections/{collection.pk}/items/{items[0]['id']}")
    collection.refresh_from_db()
    assert collection.items_count == 1


def test_one_mod_in_two_collections():
    owner = UserFactory()
    first, second = CollectionFactory(owner=owner), CollectionFactory(owner=owner)
    ProjectFactory(slug="sodium")
    client = client_for(owner)

    add(client, first, "sodium")
    add(client, second, "sodium")

    mine = client.get("/api/v1/me/collections", {"kind": "mod", "id": "sodium"}).json()
    assert {item["id"]: item["contains"] for item in mine} == {first.pk: True, second.pk: True}
    assert all(item["item_id"] for item in mine)


def test_others_cannot_edit():
    collection = CollectionFactory(visibility=Visibility.PUBLIC)
    ProjectFactory(slug="sodium")
    stranger = client_for(UserFactory())

    assert add(stranger, collection, "sodium").status_code == 403
    assert (
        stranger.patch(
            f"/api/v1/collections/{collection.pk}", {"title": "x"}, format="json"
        ).status_code
        == 403
    )
    assert stranger.delete(f"/api/v1/collections/{collection.pk}").status_code == 403


def test_editors_add_items_but_only_the_owner_manages_editors_and_deletes():
    owner, editor = UserFactory(), UserFactory(nickname="Helper")
    collection = CollectionFactory(owner=owner)
    ProjectFactory(slug="sodium")

    response = client_for(owner).patch(
        f"/api/v1/collections/{collection.pk}", {"editors": ["helper"]}, format="json"
    )
    assert response.json()["editors"] == ["Helper"]

    editor_client = client_for(editor)
    assert add(editor_client, collection, "sodium").status_code == 200
    assert (
        editor_client.patch(
            f"/api/v1/collections/{collection.pk}", {"editors": []}, format="json"
        ).status_code
        == 403
    )
    assert editor_client.delete(f"/api/v1/collections/{collection.pk}").status_code == 403


def test_unknown_editor_is_reported(auth_client, user):
    collection = CollectionFactory(owner=user)

    response = auth_client.patch(
        f"/api/v1/collections/{collection.pk}", {"editors": ["ghost"]}, format="json"
    )

    assert response.status_code == 400
    assert "editors" in response.json()["fields"]


def test_reorder_needs_every_item_exactly_once(auth_client, user):
    collection = CollectionFactory(owner=user)
    for slug in ("a-mod", "b-mod", "c-mod"):
        ProjectFactory(slug=slug)
        add(auth_client, collection, slug)
    ids = list(collection.items.values_list("pk", flat=True))

    bad = auth_client.post(
        f"/api/v1/collections/{collection.pk}/reorder", {"item_ids": ids[:2]}, format="json"
    )
    good = auth_client.post(
        f"/api/v1/collections/{collection.pk}/reorder", {"item_ids": ids[::-1]}, format="json"
    )

    assert bad.status_code == 400
    assert [item["target_id"] for item in good.json()["items"]] == ["c-mod", "b-mod", "a-mod"]


def test_copy_makes_a_private_copy_for_the_viewer(auth_client, user):
    source = CollectionFactory(visibility=Visibility.LINK, share_token="tok", title="Сетап Steve")
    project = ProjectFactory(slug="sodium")
    CollectionItem.objects.create(
        collection=source, content_type_id=_ct(project), object_id=project.pk, position=1, note="!"
    )

    response = auth_client.post(f"/api/v1/collections/{source.pk}/copy?share_token=tok")

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Сетап Steve (копія)"
    assert data["visibility"] == "private"
    assert data["items_count"] == 1
    assert data["items"][0]["note"] == "!"
    copy = Collection.objects.get(pk=data["id"])
    assert copy.owner == user and copy.copied_from == source


def test_copy_of_an_inaccessible_collection_is_404(auth_client):
    source = CollectionFactory(visibility=Visibility.PRIVATE)

    assert auth_client.post(f"/api/v1/collections/{source.pk}/copy").status_code == 404


def test_public_list_shows_non_empty_public_collections(api_client):
    owner = UserFactory(nickname="Steve")
    shown = CollectionFactory(owner=owner)
    CollectionFactory(owner=owner, visibility=Visibility.PRIVATE, items_count=3)
    CollectionFactory(owner=owner)  # empty
    Collection.objects.filter(pk=shown.pk).update(items_count=1)

    data = api_client.get("/api/v1/collections", {"owner": "steve"}).json()
    assert [item["id"] for item in data["results"]] == [shown.pk]

    owner.settings.collections_visible = False
    owner.settings.save()
    assert api_client.get("/api/v1/collections", {"owner": "steve"}).json()["count"] == 0


def test_public_list_has_no_n_plus_one(api_client, django_assert_max_num_queries):
    for _ in range(6):
        collection = CollectionFactory()
        for _ in range(3):
            project = ProjectFactory(icon_url="https://cdn.modrinth.com/data/x/icon.webp")
            CollectionItem.objects.create(
                collection=collection, content_type_id=_ct(project), object_id=project.pk
            )
        Collection.objects.filter(pk=collection.pk).update(items_count=3)

    with django_assert_max_num_queries(6):
        response = api_client.get("/api/v1/collections")
    assert len(response.json()["results"]) == 6
    assert len(response.json()["results"][0]["preview"]) == 3


def _ct(project) -> int:
    from django.contrib.contenttypes.models import ContentType

    return ContentType.objects.get_for_model(project).pk


def test_public_list_has_no_n_plus_one_for_players(auth_client, django_assert_max_num_queries):
    for _ in range(8):
        CollectionFactory(visibility=Collection.Visibility.PUBLIC, items_count=1)

    with django_assert_max_num_queries(6):
        response = auth_client.get("/api/v1/collections")

    assert len(response.json()["results"]) == 8
    assert not any(item["can_edit"] for item in response.json()["results"])
