import pytest
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.mods.models import Project
from apps.mods.tests.factories import ProjectFactory
from apps.notifications.models import Notification
from apps.packs.tests.factories import PackFactory
from apps.servers.tests.factories import ServerFactory
from apps.translations.models import Translation

pytestmark = pytest.mark.django_db


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_login(user)
    return client


def moderator():
    return UserFactory(role="moderator")


def propose(user, *, kind="mod", identifier="sodium", field="summary", text="Оптимізація гри"):
    return client_for(user).post(
        "/api/v1/translations",
        {"kind": kind, "id": identifier, "field": field, "text": text},
        format="json",
    )


def decide(user, translation_id, decision="approve", reason=""):
    return client_for(user).post(
        f"/api/v1/translations/{translation_id}/review",
        {"decision": decision, "reason": reason},
        format="json",
    )


def test_proposed_approved_shown_with_byline_and_author_told():
    project = ProjectFactory(slug="sodium")
    author = UserFactory(nickname="Mavka")

    response = propose(author, field="description", text="**Найшвидший** рушій рендерингу.")
    assert response.status_code == 201
    assert decide(moderator(), response.json()["id"]).status_code == 200

    project.refresh_from_db()
    assert "<strong>Найшвидший</strong>" in project.body_uk_html
    assert project.body_uk_by == author
    page = APIClient().get("/api/v1/mods/sodium").json()
    assert page["body_uk_by"]["nickname"] == "Mavka"
    assert Notification.objects.get(user=author).type == "translation_published"


def test_a_new_approval_supersedes_the_previous_one():
    ProjectFactory(slug="sodium")
    first = propose(UserFactory(), text="Перший").json()["id"]
    second = propose(UserFactory(), text="Другий").json()["id"]
    boss = moderator()

    decide(boss, first)
    decide(boss, second)

    assert Translation.objects.get(pk=first).status == "superseded"
    assert Project.objects.get(slug="sodium").summary_uk == "Другий"


def test_rejection_tells_the_author_why():
    ProjectFactory(slug="sodium")
    author = UserFactory()
    translation_id = propose(author).json()["id"]

    decide(moderator(), translation_id, "reject", "Машинний переклад")

    note = Notification.objects.get(user=author)
    assert (note.type, note.payload["reason"]) == ("translation_rejected", "Машинний переклад")
    assert Project.objects.get(slug="sodium").summary_uk == ""


def test_only_moderators_decide_and_only_once():
    ProjectFactory(slug="sodium")
    translation_id = propose(UserFactory()).json()["id"]
    boss = moderator()

    assert decide(UserFactory(), translation_id).status_code == 403
    assert decide(boss, translation_id).status_code == 200
    assert decide(boss, translation_id).json()["code"] == "already_reviewed"


def test_one_pending_per_author_and_field():
    ProjectFactory(slug="sodium")
    author = UserFactory()

    propose(author, text="Раз")
    propose(author, text="Два")

    assert list(Translation.objects.values_list("text", flat=True)) == ["Два"]


def test_only_what_came_from_modrinth_is_translated():
    community = PackFactory()
    modrinth = PackFactory(origin="modrinth")
    owned = ServerFactory(owned=True)
    mirrored = ServerFactory()
    player = UserFactory()

    assert propose(player, kind="pack", identifier=community.slug).json()["code"] == (
        "not_translatable"
    )
    assert propose(player, kind="pack", identifier=modrinth.slug).status_code == 201
    assert propose(player, kind="server", identifier=owned.slug).status_code == 400
    assert propose(player, kind="server", identifier=mirrored.slug).status_code == 201


def test_page_lists_published_my_pending_and_all_pending_for_moderators():
    ProjectFactory(slug="sodium")
    mine, other = UserFactory(), UserFactory()
    propose(mine, text="Мій")
    propose(other, text="Чужий")
    query = {"kind": "mod", "id": "sodium"}

    assert APIClient().get("/api/v1/translations", query).json() == []
    assert [t["text"] for t in client_for(mine).get("/api/v1/translations", query).json()] == [
        "Мій"
    ]
    assert len(client_for(moderator()).get("/api/v1/translations", query).json()) == 2
    assert client_for(moderator()).get("/api/v1/translations/queue").json()["count"] == 2


def test_banned_words_are_refused():
    from apps.moderation.models import BannedWord
    from apps.moderation.words import forget_cache

    ProjectFactory(slug="sodium")
    BannedWord.objects.create(word="поганець", language="uk")
    forget_cache()

    assert propose(UserFactory(), text="Ти поганець").status_code == 400


def test_guests_cannot_propose():
    ProjectFactory(slug="sodium")

    response = APIClient().post(
        "/api/v1/translations",
        {"kind": "mod", "id": "sodium", "field": "summary", "text": "x"},
        format="json",
    )

    assert response.status_code == 401


def test_a_moderator_does_not_approve_their_own_translation():
    ProjectFactory(slug="sodium")
    boss = moderator()
    translation_id = propose(boss).json()["id"]

    assert decide(boss, translation_id).json()["code"] == "own_translation"


def test_images_in_a_player_description_are_dropped():
    project = ProjectFactory(slug="sodium")
    translation_id = propose(
        UserFactory(), field="description", text="Опис ![x](https://tracker.example/p.png)"
    ).json()["id"]

    decide(moderator(), translation_id)

    project.refresh_from_db()
    assert "<img" not in project.body_uk_html and "Опис" in project.body_uk_html


def test_queue_has_no_n_plus_one(django_assert_max_num_queries):
    for n in range(6):
        ProjectFactory(slug=f"mod-{n}")
        propose(UserFactory(), identifier=f"mod-{n}")
    boss = client_for(moderator())

    with django_assert_max_num_queries(8):
        data = boss.get("/api/v1/translations/queue").json()
    assert {row["target_id"] for row in data["results"]} == {f"mod-{n}" for n in range(6)}


def test_approved_summary_shows_on_pack_cards():
    pack = PackFactory(origin="modrinth", summary="Tech pack")
    translation_id = propose(
        UserFactory(), kind="pack", identifier=pack.slug, text="Технічна збірка"
    ).json()["id"]

    decide(moderator(), translation_id)

    card = APIClient().get("/api/v1/packs", {"all": "1"}).json()["results"][0]
    assert card["summary"] == "Технічна збірка"
