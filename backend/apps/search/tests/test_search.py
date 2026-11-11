import httpx
import pytest
import respx

from apps.library.tests.factories import CollectionFactory
from apps.mods.tests.factories import CategoryFactory, ProjectFactory
from apps.packs.tests.factories import PackFactory, add, mod
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
        results = []
        for query in queries:
            kind = query["filter"].split('"')[1]
            # Hits per kind, or per (kind, q) to tell the query as typed from its twin
            found = self.hits.get((kind, query["q"]), self.hits.get(kind, []))
            if (kind, query["q"]) in self.hits:
                start = query.get("offset", 0)
                page = found[start : start + query["limit"]]
                results.append({"hits": page, "estimatedTotalHits": len(found)})
            else:
                results.append({"hits": found, "estimatedTotalHits": 7})
        return results


# Documents


def test_mod_document_has_search_fields():
    category = CategoryFactory(slug="optimization", name_uk="Оптимізація")
    project = ProjectFactory(slug="sodium", title="Sodium", categories=[category])

    doc = documents.document_for("mod", project.pk)

    assert doc["uid"] == f"mod-{project.pk}"
    assert (doc["kind"], doc["id"], doc["title"]) == ("mod", "sodium", "Sodium")
    assert set(doc["tags"]) == {"optimization", "Оптимізація", "mod", "мод"}
    assert doc["latest_game_version"] == "26.3"
    assert doc["popularity"] == 1000


def test_only_public_objects_are_searchable():
    pending = SkinFactory(is_hidden=True)
    private = CollectionFactory(visibility="private", items_count=3)
    empty = CollectionFactory(items_count=0)

    assert documents.document_for("skin", pending.pk) is None
    assert documents.document_for("collection", private.pk) is None
    assert documents.document_for("collection", empty.pk) is None


def test_server_and_skin_documents():
    server = ServerFactory(name="Січ", categories=["survival", "roleplay"])
    skin = SkinFactory(title="Мавка", color_bucket="green")

    server_doc = documents.document_for("server", server.pk)
    skin_doc = documents.document_for("skin", skin.pk)

    assert (server_doc["id"], server_doc["modes"], server_doc["address"]) == (
        server.slug,
        ["survival", "roleplay"],
        server.address,
    )
    assert (skin_doc["id"], skin_doc["color_bucket"], skin_doc["author"]) == (
        str(skin.pk),
        "green",
        None,
    )
    # R8: where it comes from and which languages a server speaks
    assert (server_doc["source"], server_doc["languages"]) == ("modrinth", ["uk"])
    assert skin_doc["source"] == skin.source


def test_pack_documents_say_where_they_come_from():
    official = PackFactory(origin="modrinth")
    community = PackFactory()

    assert documents.document_for("pack", official.pk)["source"] == "modrinth"
    assert documents.document_for("pack", community.pk)["source"] is None


def test_pack_document_is_found_by_the_mods_inside():
    pack = PackFactory(title="Техно Січ", loader="neoforge")
    add(pack, mod(title="Create"))
    draft = PackFactory(status="draft")
    by_link = PackFactory(visibility="link")

    doc = documents.document_for("pack", pack.pk)

    assert doc["tags"] == ["Create"]
    assert (doc["loaders"], doc["latest_game_version"], doc["items_count"]) == (
        ["neoforge"],
        "26.3",
        1,
    )
    assert doc["author"] == pack.author.nickname
    assert documents.document_for("pack", draft.pk) is None
    assert documents.document_for("pack", by_link.pk) is None


# Indexing


def test_index_object_adds_and_removes():
    fake = FakeMeili()
    skin = SkinFactory()

    assert services.index_object(kind="skin", pk=skin.pk, client_factory=lambda: fake) is True
    assert f"skin-{skin.pk}" in fake.documents["content"]

    Skin.objects.filter(pk=skin.pk).update(is_hidden=True)
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
        'kind = "pack"',
        'kind = "skin"',
        'kind = "server"',
        'kind = "collection"',
    ]
    assert {q["limit"] for q in queries} == {5}


def test_search_one_kind_pages_through_results():
    fake = FakeMeili(hits={"server": [hit("server", "Січ")]})

    [group] = services.search(q="sich", kind="server", page=2, client_factory=lambda: fake)

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
    assert api_client.get("/api/v1/search", {"q": "x", "kind": "world"}).status_code == 400


@pytest.mark.usefixtures("game_versions")
def test_search_endpoint_uses_my_game_of_the_guest(api_client, monkeypatch):
    from apps.core.game import GAME_COOKIE

    fabric = ProjectFactory(slug="sodium", game_versions=["26.3"], loaders=["fabric"])
    forge = ProjectFactory(slug="forge-only", game_versions=["26.3"], loaders=["forge"])
    skin = SkinFactory()
    fake = FakeMeili(
        hits={
            "mod": [documents.document_for("mod", p.pk) for p in (fabric, forge)],
            "skin": [documents.document_for("skin", skin.pk)],
        }
    )
    monkeypatch.setattr(services, "MeiliClient", lambda: fake)
    api_client.cookies[GAME_COOKIE] = "26.3:fabric"

    body = api_client.get("/api/v1/search", {"q": "x", "mine": "1"}).json()

    fits = {h["id"]: h["fits_my_game"] for g in body["groups"] for h in g["results"]}
    assert fits == {"sodium": True, "forge-only": False, str(skin.pk): None}
    mod_filter = next(q["filter"] for q in fake.calls[-1][1] if '"mod"' in q["filter"])
    assert 'game_versions = "26.3"' in mod_filter


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


# R8: Ukrainian queries and «Моя гра»


def test_cyrillic_query_is_also_searched_in_latin():
    from apps.search.services import latin_twin

    assert latin_twin("содіум") == "sodium"
    assert latin_twin("Іріс") == "iris"
    assert latin_twin("sodium") is None


def test_twin_query_hits_are_merged_without_duplicates():
    fake = FakeMeili(hits={"mod": [{"uid": "mod-1", "kind": "mod", "id": "sodium"}]})

    groups = services.search(q="содіум", kind="mod", client_factory=lambda: fake)

    queries = fake.calls[-1][1]
    assert [query["q"] for query in queries] == ["содіум", "sodium"]
    assert [hit["id"] for hit in groups[0]["results"]] == ["sodium"]


def _hits(prefix: str, count: int) -> list[dict]:
    return [{"uid": f"mod-{prefix}{n}", "kind": "mod", "id": f"{prefix}{n}"} for n in range(count)]


def test_twin_hits_come_after_the_query_as_typed_and_count_in_the_total():
    typed, twin = _hits("a", 4), [*_hits("a", 1), *_hits("b", 3)]
    fake = FakeMeili(hits={("mod", "содіум"): typed, ("mod", "sodium"): twin})

    group = services.search(q="содіум", client_factory=lambda: fake)[0]

    assert [hit["id"] for hit in group["results"]] == ["a0", "a1", "a2", "a3", "b0"]
    # 4 + 3 new ones: «Показати всі» appears although each query alone found ≤ 5
    assert group["total"] > len(group["results"])


def test_twin_hits_are_paged_without_losses_or_repeats():
    typed, twin = _hits("a", 30), [*_hits("a", 2), *_hits("b", 10)]
    fake = FakeMeili(hits={("mod", "содіум"): typed, ("mod", "sodium"): twin})

    def page(number: int) -> list[str]:
        group = services.search(q="содіум", kind="mod", page=number, client_factory=lambda: fake)
        return [hit["id"] for hit in group[0]["results"]]

    first, second = page(1), page(2)

    assert first == [f"a{n}" for n in range(24)]
    assert second == [*(f"a{n}" for n in range(24, 30)), *(f"b{n}" for n in range(10))]


def test_the_database_fallback_keeps_my_game_and_the_twin():
    from apps.core.game import GameContext

    ProjectFactory(slug="sodium", title="Sodium", game_versions=["26.3"], loaders=["fabric"])
    ProjectFactory(
        slug="sodium-forge", title="Sodium Forge", game_versions=["26.3"], loaders=["forge"]
    )
    game = GameContext("26.3", "fabric", "cookie")

    groups = services.search(
        q="содіум",
        kind="mod",
        game=game,
        only_my_game=True,
        client_factory=lambda: FakeMeili(down=True),
    )

    assert [(hit["id"], hit["fits_my_game"]) for hit in groups[0]["results"]] == [("sodium", True)]


def test_only_my_game_filters_mods_and_packs():
    from apps.core.game import GameContext

    fake = FakeMeili()
    game = GameContext("1.21.1", "fabric", "cookie")

    services.search(q="map", game=game, only_my_game=True, client_factory=lambda: fake)

    filters = {query["filter"] for query in fake.calls[-1][1]}
    mod_filter = (
        'kind = "mod" AND game_versions = "1.21.1" AND '
        '(project_type != "mod" OR loaders = "fabric")'
    )
    assert mod_filter in filters
    assert 'kind = "pack" AND game_versions = "1.21.1" AND loaders = "fabric"' in filters
    assert 'kind = "skin"' in filters


def test_hits_say_whether_they_fit_my_game():
    from apps.core.game import GameContext
    from apps.search.services import fits

    game = GameContext("1.21.1", "fabric", "cookie")
    mod = {"kind": "mod", "project_type": "mod", "game_versions": ["1.21.1"], "loaders": ["forge"]}
    shader = {
        "kind": "mod",
        "project_type": "shader",
        "game_versions": ["1.21.1"],
        "loaders": ["iris"],
    }

    assert fits(mod, game) is False
    assert fits(shader, game) is True
    assert fits({"kind": "skin"}, game) is None
    assert fits(mod, None) is None


def test_a_vanilla_game_takes_packs_of_any_loader():
    from apps.core.game import GameContext
    from apps.search.services import fits, game_filter

    game = GameContext("1.21.1", "vanilla", "cookie")
    pack = {"kind": "pack", "game_versions": ["1.21.1"], "loaders": ["fabric"]}

    assert game_filter("pack", game) == 'game_versions = "1.21.1"'
    assert fits(pack, game) is True


def test_index_knows_ukrainian_synonyms_and_types():
    from apps.search.documents import INDEX_SETTINGS

    assert "shader" in INDEX_SETTINGS["synonyms"]["шейдери"]
    assert "minimap" in INDEX_SETTINGS["synonyms"]["мінікарта"]
    project = ProjectFactory(slug="complementary", project_type="shader")

    doc = documents.document_for("mod", project.pk)

    assert {"shader", "шейдер"} <= set(doc["tags"])
    assert doc["source"] == "modrinth"
