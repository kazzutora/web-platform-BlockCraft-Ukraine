import httpx
import pytest
import respx

from apps.library.tests.factories import CollectionFactory
from apps.mods.tests.factories import CategoryFactory, ProjectFactory
from apps.search import documents, services, signals
from apps.search.client import MeiliClient, SearchUnavailableError
from apps.servers.tests.factories import ServerFactory
from apps.skins.models import Skin
from apps.skins.tests.factories import SkinFactory

pytestmark = pytest.mark.django_db


class FakeMeili:
    """Records what the services ask Meilisearch to do."""

    def __init__(self, *, indexes=("content",), hits=None, down=False):
        self.indexes = set(indexes)
        self.hits = hits or {}
        self.down = down
        self.calls: list[tuple] = []
        self.documents: dict[str, dict[str, dict]] = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def _task(self, *call):
        self.calls.append(call)
        return {"taskUid": len(self.calls)}

    def wait(self, task, timeout=60):
        return {"status": "succeeded"}

    def index_exists(self, uid):
        return uid in self.indexes

    def create_index(self, uid, *, primary_key):
        self.indexes.add(uid)
        return self._task("create", uid, primary_key)

    def delete_index(self, uid):
        self.indexes.discard(uid)
        return self._task("delete_index", uid)

    def update_settings(self, uid, settings):
        return self._task("settings", uid)

    def add_documents(self, uid, docs):
        self.documents.setdefault(uid, {}).update({d["uid"]: d for d in docs})
        return self._task("add", uid, [d["uid"] for d in docs])

    def delete_documents(self, uid, ids):
        for doc_id in ids:
            self.documents.get(uid, {}).pop(doc_id, None)
        return self._task("delete", uid, ids)

    def swap_indexes(self, first, second):
        return self._task("swap", first, second)

    def multi_search(self, queries):
        if self.down:
            raise SearchUnavailableError("down")
        self.calls.append(("search", queries))
        return [
            {"hits": self.hits.get(query["filter"].split('"')[1], []), "estimatedTotalHits": 7}
            for query in queries
        ]


# Documents


def test_mod_document_has_search_fields():
    category = CategoryFactory(slug="optimization", name_uk="Оптимізація")
    project = ProjectFactory(slug="sodium", title="Sodium", categories=[category])

    doc = documents.document_for("mod", project.pk)

    assert doc["uid"] == f"mod-{project.pk}"
    assert (doc["kind"], doc["id"], doc["title"]) == ("mod", "sodium", "Sodium")
    assert set(doc["tags"]) == {"optimization", "Оптимізація"}
    assert doc["latest_game_version"] == "26.3"
    assert doc["popularity"] == 1000


def test_only_public_objects_are_searchable():
    pending = SkinFactory(status=Skin.Status.PENDING)
    private = CollectionFactory(visibility="private", items_count=3)
    empty = CollectionFactory(items_count=0)

    assert documents.document_for("skin", pending.pk) is None
    assert documents.document_for("collection", private.pk) is None
    assert documents.document_for("collection", empty.pk) is None


def test_server_and_skin_documents():
    server = ServerFactory(name="Січ", modes=["survival", "rp"])
    skin = SkinFactory(title="Мавка", color_bucket="green", style_tags=["ukrainian"])

    server_doc = documents.document_for("server", server.pk)
    skin_doc = documents.document_for("skin", skin.pk)

    assert (server_doc["id"], server_doc["modes"], server_doc["address"]) == (
        server.slug,
        ["survival", "rp"],
        server.address,
    )
    assert (skin_doc["id"], skin_doc["color_bucket"], skin_doc["author"]) == (
        str(skin.pk),
        "green",
        skin.author.nickname,
    )


# Indexing


def test_index_object_adds_and_removes():
    fake = FakeMeili()
    skin = SkinFactory()

    assert services.index_object(kind="skin", pk=skin.pk, client_factory=lambda: fake) is True
    assert f"skin-{skin.pk}" in fake.documents["content"]

    Skin.objects.filter(pk=skin.pk).update(status=Skin.Status.HIDDEN)
    assert services.index_object(kind="skin", pk=skin.pk, client_factory=lambda: fake) is False
    assert f"skin-{skin.pk}" not in fake.documents["content"]


def test_missing_index_is_created_with_settings():
    fake = FakeMeili(indexes=())

    services.index_object(kind="mod", pk=ProjectFactory().pk, client_factory=lambda: fake)

    assert fake.calls[:2] == [("create", "content", "uid"), ("settings", "content")]


def test_reindex_builds_a_fresh_index_and_swaps_it():
    ProjectFactory.create_batch(3)
    SkinFactory()
    ServerFactory()
    fake = FakeMeili(indexes=("content", "content_fresh"))

    count = services.reindex_all(client_factory=lambda: fake, batch=2)

    assert count == 5
    names = [call[0] for call in fake.calls]
    assert names[0] == "delete_index"  # leftovers of a failed run
    assert names[-2:] == ["swap", "delete_index"]
    assert len(fake.documents["content_fresh"]) == 5


def test_signals_queue_index_updates(settings, django_capture_on_commit_callbacks, monkeypatch):
    queued = []
    monkeypatch.setattr(
        "apps.search.tasks.index_object.delay", lambda *a: queued.append(("index", *a))
    )
    monkeypatch.setattr(
        "apps.search.tasks.remove_object.delay", lambda *a: queued.append(("remove", *a))
    )
    settings.SEARCH_INDEXING = True

    with django_capture_on_commit_callbacks(execute=True):
        server = ServerFactory()
    pk = server.pk
    with django_capture_on_commit_callbacks(execute=True):
        server.delete()

    assert queued == [("index", "server", pk), ("remove", "server", pk)]


def test_signals_are_off_when_indexing_is_disabled(django_capture_on_commit_callbacks, monkeypatch):
    queued = []
    monkeypatch.setattr("apps.search.tasks.index_object.delay", lambda *a: queued.append(a))

    with django_capture_on_commit_callbacks(execute=True):
        ServerFactory()

    assert queued == []
    assert signals.settings.SEARCH_INDEXING is False


# Searching


def hit(kind, title):
    return {"kind": kind, "id": title.lower(), "title": title}


def test_search_groups_results_by_kind():
    fake = FakeMeili(hits={"mod": [hit("mod", "Sodium")], "skin": [hit("skin", "Мавка")]})

    groups = services.search(q="sodim", client_factory=lambda: fake)

    assert [(g["kind"], [h["title"] for h in g["results"]]) for g in groups] == [
        ("mod", ["Sodium"]),
        ("skin", ["Мавка"]),
    ]
    queries = fake.calls[-1][1]
    assert [q["filter"] for q in queries] == [
        'kind = "mod"',
        'kind = "skin"',
        'kind = "server"',
        'kind = "collection"',
    ]
    assert {q["limit"] for q in queries} == {5}


def test_search_one_kind_pages_through_results():
    fake = FakeMeili(hits={"server": [hit("server", "Січ")]})

    [group] = services.search(q="січ", kind="server", page=2, client_factory=lambda: fake)

    query = fake.calls[-1][1][0]
    assert (query["limit"], query["offset"]) == (24, 24)
    assert (group["total"], group["next_page"]) == (7, None)


def test_search_falls_back_to_the_database():
    ProjectFactory(title="Sodium")
    ProjectFactory(title="Lithium")

    groups = services.search(q="sodi", client_factory=lambda: FakeMeili(down=True))

    assert [(g["kind"], [h["title"] for h in g["results"]]) for g in groups] == [
        ("mod", ["Sodium"])
    ]


def test_search_endpoint(api_client, monkeypatch):
    fake = FakeMeili(
        hits={"mod": [documents.document_for("mod", ProjectFactory(title="Sodium").pk)]}
    )
    monkeypatch.setattr(services, "MeiliClient", lambda: fake)

    body = api_client.get("/api/v1/search", {"q": "sodim"}).json()

    assert body["q"] == "sodim"
    assert body["groups"][0]["results"][0]["title"] == "Sodium"
    assert api_client.get("/api/v1/search").status_code == 400
    assert api_client.get("/api/v1/search", {"q": "x", "kind": "pack"}).status_code == 400


@respx.mock
def test_client_sends_the_key_and_reports_errors():
    route = respx.post("http://meili.test:7700/multi-search").respond(json={"results": []})
    with MeiliClient(key="secret") as client:
        assert client.multi_search([]) == []
    assert route.calls.last.request.headers["Authorization"] == "Bearer secret"

    respx.post("http://meili.test:7700/multi-search").mock(side_effect=httpx.ConnectError("no"))
    with MeiliClient(key="secret") as client, pytest.raises(SearchUnavailableError):
        client.multi_search([])


@respx.mock
def test_client_waits_for_index_tasks():
    base = "http://meili.test:7700"
    respx.post(f"{base}/indexes").respond(202, json={"taskUid": 7})
    respx.get(f"{base}/tasks/7").mock(
        side_effect=[
            httpx.Response(200, json={"status": "processing"}),
            httpx.Response(200, json={"status": "succeeded"}),
        ]
    )
    respx.get(f"{base}/indexes/content").respond(404, json={"code": "index_not_found"})
    respx.patch(f"{base}/indexes/content/settings").respond(202, json={"taskUid": 8})
    respx.get(f"{base}/tasks/8").respond(json={"status": "failed", "error": {"code": "bad"}})

    with MeiliClient(key="", sleep=lambda seconds: None) as client:
        assert client.index_exists("content") is False
        assert (
            client.wait(client.create_index("content", primary_key="uid"))["status"] == "succeeded"
        )
        with pytest.raises(SearchUnavailableError):
            client.wait(client.update_settings("content", {}))


def test_reindex_command(monkeypatch):
    calls = []
    monkeypatch.setattr(services, "reindex_all", lambda: calls.append(1) or 3)
    from django.core.management import call_command

    call_command("reindex_search")

    assert calls == [1]
