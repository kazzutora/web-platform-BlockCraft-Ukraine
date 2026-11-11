"""Modrinth v3 server projects → Server, on the recorded answers (fixtures: modrinth_v3/)."""

from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone

from apps.core.models import Source
from apps.packs.models import Origin, Pack
from apps.packs.tests.factories import PackFactory
from apps.servers import importers, services
from apps.servers.importers import Outcome
from apps.servers.models import ContentKind, Server
from apps.sources.clients.modrinth import ModrinthNotFoundError
from apps.sources.models import SyncRun
from apps.sources.runs import SyncCounter
from apps.sources.schemas.modrinth_v3 import ServerProject, ServerSearchResponse
from apps.sources.tests.recorded import load

from .factories import ServerFactory

pytestmark = pytest.mark.django_db


def project(name: str, **changes) -> ServerProject:
    return ServerProject.model_validate({**load("modrinth_v3", name), **changes})


def test_vanilla_server_keeps_its_versions_and_links():
    server, outcome = importers.import_server(project("project_server_vanilla"))

    assert outcome == Outcome.CREATED
    assert (server.source, server.external_id) == (Source.MODRINTH, "t64zvHbD")
    assert server.external_url == "https://modrinth.com/server/the-vee-hive-minecraft-server"
    assert (server.java_host, server.java_port) == ("dominica-spot.tun.ply.gg", 25565)
    assert server.content_kind == ContentKind.VANILLA
    assert (server.supported_versions, server.recommended_version) == (["26.2"], "26.2")
    assert server.languages == ["en"]
    assert server.categories == ["adventure-mode", "economy"]
    assert server.website_url and server.discord_url
    assert server.description_html and server.icon_url
    assert not server.is_verified and server.owner is None


def test_modded_server_with_its_own_pack_remembers_what_to_import():
    server, _ = importers.import_server(project("project_server_uk"))

    assert server.content_kind == ContentKind.MODDED
    assert (server.modpack_project_id, server.modpack_version_id) == ("hMclbsMN", "JsOtePr6")
    assert server.languages == ["ru", "be", "uk"]
    assert server.banner_url.startswith("https://cdn.modrinth.com/")
    assert importers.needs_pack(server)


def test_server_without_counted_plays_imports_with_zero():
    server, outcome = importers.import_server(project("project_server_no_plays"))

    assert (outcome, server.modrinth_plays) == (Outcome.CREATED, 0)


def test_modded_server_with_a_separate_modpack():
    server, _ = importers.import_server(project("project_server_external_pack"))

    assert server.modpack_project_id == "shAGUyEd"
    assert server.required_pack is None and importers.needs_pack(server)


def test_second_import_is_unchanged_until_modrinth_changes_the_page():
    data = project("project_server_vanilla")
    importers.import_server(data)

    _, again = importers.import_server(data)
    _, changed = importers.import_server(
        project("project_server_vanilla", updated=(timezone.now() + timedelta(days=1)).isoformat())
    )

    assert (again, changed) == (Outcome.UNCHANGED, Outcome.UPDATED)
    assert Server.objects.count() == 1


def test_hidden_server_stays_hidden():
    server, _ = importers.import_server(project("project_server_uk"))
    Server.objects.filter(pk=server.pk).update(is_hidden=True)

    importers.import_server(
        project("project_server_uk", updated=(timezone.now() + timedelta(days=1)).isoformat())
    )

    assert Server.objects.get(pk=server.pk).is_hidden


class FakeV3:
    def __init__(self):
        self.pages = {
            "uk": load("modrinth_v3", "search_servers_uk"),
            None: load("modrinth_v3", "search_servers"),
        }
        self.projects = {
            name: load("modrinth_v3", f"project_server_{name}")
            for name in ("1", "2", "3", "uk", "vanilla", "external_pack")
        }

    def search_servers(
        self, *, language=None, content_kind=None, index="relevance", offset=0, limit=20
    ):
        # Only the servers whose project answer was recorded
        page = dict(self.pages[language])
        known = {item["id"] for item in self.projects.values()}
        recorded = [hit for hit in page["hits"] if hit["project_id"] in known]
        hits = recorded[offset : offset + limit]
        return ServerSearchResponse.model_validate(
            {**page, "hits": hits, "total_hits": len(recorded)}
        )

    def get_server(self, project_id):
        for item in self.projects.values():
            if item["id"] == project_id:
                return ServerProject.model_validate(item)
        raise LookupError(project_id)


def test_sync_takes_ukrainian_servers_first_and_queues_their_packs():
    fake = FakeV3()
    run = SyncCounter()

    packs = services.sync_modrinth(client=fake, limit=10, run=run, progress=lambda m: None)

    slugs = list(Server.objects.order_by("pk").values_list("slug", flat=True))
    assert slugs[0] == "submine"  # the Ukrainian-speaking one came first
    assert run.created == Server.objects.count() >= 3
    assert run.failed == 0
    assert set(packs) == set(
        Server.objects.filter(content_kind=ContentKind.MODDED).values_list("pk", flat=True)
    )


def test_sync_task_writes_a_sync_run(settings):
    settings.SYNC_LIMITS = {**settings.SYNC_LIMITS, "servers": 4}
    from apps.servers import tasks

    with (
        mock.patch("apps.servers.tasks.ModrinthV3Client") as factory,
        mock.patch("apps.servers.tasks.import_required_pack.delay") as delay,
    ):
        factory.return_value.__enter__.return_value = FakeV3()
        result = tasks.sync_modrinth.delay().get()

    assert result["created"] == 4
    assert SyncRun.objects.get(job="modrinth.servers").params == {"limit": 4}
    assert delay.call_count == Server.objects.filter(content_kind=ContentKind.MODDED).count()


def later(name: str) -> ServerProject:
    """The same project after a change on Modrinth."""
    return project(name, updated=(timezone.now() + timedelta(days=1)).isoformat())


def test_an_owner_keeps_what_they_wrote(user):
    server, _ = importers.import_server(project("project_server_vanilla"))
    pack = PackFactory(author=user)
    Server.objects.filter(pk=server.pk).update(
        owner=user,
        is_verified=True,
        summary="Наш сервер",
        discord_url="https://discord.gg/mine",
        required_pack=pack,
        pack_chosen_by_owner=True,
    )

    importers.import_server(later("project_server_vanilla"))

    server.refresh_from_db()
    assert (server.summary, server.discord_url) == ("Наш сервер", "https://discord.gg/mine")
    # A vanilla server on Modrinth still needs the owner's pack here
    assert (server.required_pack, server.content_kind) == (pack, ContentKind.MODDED)
    assert not importers.needs_pack(server)


def test_owner_added_server_becomes_the_modrinth_one_with_the_same_address(user):
    data = project("project_server_vanilla")
    host, port = importers.normalize_address(data.minecraft_java_server.address)
    added = ServerFactory(
        source=Source.OWNER,
        external_id=f"{host}:{port}",
        java_host=host,
        java_port=port,
        owner=user,
        is_verified=True,
    )

    server, outcome = importers.import_server(data)

    assert (server.pk, outcome) == (added.pk, Outcome.UPDATED)
    assert (server.source, server.external_id, server.owner) == (Source.MODRINTH, data.id, user)
    assert Server.objects.count() == 1


def test_addresses_and_links_from_modrinth_are_cleaned():
    data = project("project_server_vanilla")
    java = data.minecraft_java_server.model_copy(update={"address": "http://Play.Example.COM./"})
    links = {
        "discord": data.link_urls["discord"].model_copy(update={"url": "javascript:alert(1)"}),
    }

    server, _ = importers.import_server(
        data.model_copy(update={"minecraft_java_server": java, "link_urls": links})
    )

    assert (server.java_host, server.java_port) == ("play.example.com", 25565)
    assert server.discord_url == ""


def test_reserved_slugs_are_not_taken():
    assert importers.unique_slug("add") == "add-server"


def test_a_server_gone_from_modrinth_is_hidden():
    class Gone(FakeV3):
        def get_server(self, project_id):
            if project_id == "OLD00001":
                raise ModrinthNotFoundError(project_id)
            return super().get_server(project_id)

    old = ServerFactory(external_id="OLD00001", synced_at=timezone.now() - timedelta(days=3))
    run = SyncCounter()

    services.sync_modrinth(client=Gone(), limit=2, run=run, progress=lambda m: None)

    old.refresh_from_db()
    assert old.is_hidden and old.hidden_reason
    assert run.failed == 0


def test_a_pack_uploaded_into_the_server_follows_the_version_it_names(user):
    server = ServerFactory(
        external_id="SERVER01",
        content_kind=ContentKind.MODDED,
        modpack_project_id="SERVER01",
        modpack_version_id="PACKV001",
    )
    pack = PackFactory(
        origin=Origin.MODRINTH, external_id="SERVER01", modrinth_version_id="PACKV001"
    )
    client = mock.Mock()
    client.get_project.return_value = mock.Mock(id="SERVER01")
    client.get_versions_by_ids.return_value = [mock.Mock(id="PACKV001")]

    with mock.patch("apps.packs.services.import_modpack", return_value=pack) as import_modpack:
        assert services.import_required_pack(server_id=server.pk, client=client)

    assert import_modpack.call_args.kwargs["version"].id == "PACKV001"
    server.refresh_from_db()
    assert server.required_pack == pack
    assert Pack.objects.get(pk=pack.pk).external_url == server.external_url
    assert not importers.needs_pack(server)


def test_a_separate_modpack_is_shared_and_never_repinned(user):
    """packs.sync_official keeps it at its newest release; servers only link to it."""
    pack = PackFactory(origin=Origin.MODRINTH, external_id="FABULOUS", modrinth_version_id="NEW")
    server = ServerFactory(
        content_kind=ContentKind.MODDED, modpack_project_id="FABULOUS", modpack_version_id="OLD"
    )
    client = mock.Mock()

    with mock.patch("apps.packs.services.import_modpack") as import_modpack:
        assert services.import_required_pack(server_id=server.pk, client=client)

    import_modpack.assert_not_called()
    server.refresh_from_db()
    assert server.required_pack == pack
    assert not importers.needs_pack(server)
