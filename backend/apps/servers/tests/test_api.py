from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from apps.core.exceptions import DomainError
from apps.core.models import Source
from apps.packs.models import Origin
from apps.packs.tests.factories import PackFactory
from apps.servers import services
from apps.servers import status as live
from apps.servers.models import ContentKind, Server
from apps.sources.clients.ping import PingResult

from .factories import ServerFactory, SnapshotFactory, fake_probe, online

pytestmark = pytest.mark.django_db


def slugs(response) -> list[str]:
    return [row["slug"] for row in response.json()["results"]]


# Owners: add, claim, verify


def test_owner_adds_a_server_that_answers(auth_client, user, monkeypatch):
    probe = fake_probe({"play.sich.ua": online(motd="Січ")})
    monkeypatch.setattr(services.clients, "ping", probe)
    monkeypatch.setattr("apps.servers.services.validators.clean_host", lambda h: h)

    response = auth_client.post("/api/v1/servers", {"address": "play.sich.ua"}, format="json")

    assert response.status_code == 201
    data = response.json()
    assert (data["address"], data["is_verified"], data["is_claimed_by_me"]) == (
        "play.sich.ua",
        False,
        True,
    )
    assert data["verify_code"].startswith("bc-")
    assert data["source"] is None
    server = Server.objects.get()
    assert (server.source, server.external_id) == (Source.OWNER, "play.sich.ua:25565")
    # Not listed until the code is in the MOTD
    assert auth_client.get("/api/v1/servers", {"all": "1"}).json()["count"] == 0


def test_a_silent_address_is_refused(auth_client, monkeypatch):
    monkeypatch.setattr(services.clients, "ping", fake_probe({}))
    monkeypatch.setattr("apps.servers.services.validators.clean_host", lambda h: h)

    response = auth_client.post("/api/v1/servers", {"address": "dead.example.com"}, format="json")

    assert (response.status_code, response.json()["code"]) == (400, "not_responding")
    assert not Server.objects.exists()


@pytest.mark.parametrize("address", ["127.0.0.1", "localhost", "10.0.0.5:25565"])
def test_internal_addresses_are_rejected(auth_client, address):
    response = auth_client.post("/api/v1/servers", {"address": address}, format="json")

    assert (response.status_code, response.json()["code"]) == (400, "invalid_address")


def test_guests_cannot_add_servers(api_client):
    assert api_client.post("/api/v1/servers", {"address": "x.example.com"}).status_code == 401


def test_claiming_a_modrinth_server_by_its_address(auth_client, user, monkeypatch):
    server = ServerFactory(java_host="mc.submine.net")
    monkeypatch.setattr("apps.servers.services.validators.clean_host", lambda h: h)

    response = auth_client.post("/api/v1/servers", {"address": "mc.submine.net"}, format="json")

    assert response.status_code == 201
    assert response.json()["slug"] == server.slug
    assert response.json()["is_claimed_by_me"] is True
    server.refresh_from_db()
    assert (server.claimant, server.owner) == (user, None)


def test_a_proved_server_cannot_be_claimed_by_another(auth_client, monkeypatch):
    ServerFactory(owned=True, java_host="mine.example.com")
    monkeypatch.setattr("apps.servers.services.validators.clean_host", lambda h: h)

    response = auth_client.post("/api/v1/servers", {"address": "mine.example.com"}, format="json")

    assert (response.status_code, response.json()["code"]) == (400, "server_owned")


def test_verification_makes_the_claimant_the_owner(
    user, django_capture_on_commit_callbacks, monkeypatch
):
    server = ServerFactory(claimant=user)
    monkeypatch.setattr(
        services.clients,
        "ping",
        fake_probe(
            {
                server.java_host: online(
                    motd=f"Вітаємо! {services.claim_code(server.pk, user.pk).upper()}"
                )
            }
        ),
    )

    with django_capture_on_commit_callbacks(execute=True):
        assert services.request_verification(server=server, user=user) == "checking"

    server.refresh_from_db()
    assert (server.is_verified, server.owner, server.claimant) == (True, user, None)
    assert live.get_verification(server.pk, user.pk) == "verified"


@pytest.mark.parametrize(
    ("motd", "state"), [("Без коду", "missing"), (None, "offline")], ids=["missing", "offline"]
)
def test_verification_without_the_code(user, monkeypatch, motd, state):
    server = ServerFactory(claimant=user)
    results = {server.java_host: online(motd=motd)} if motd else {}
    monkeypatch.setattr(services.clients, "ping", fake_probe(results))

    assert services.verify(server_id=server.pk, user_id=user.pk) == state
    server.refresh_from_db()
    assert not server.is_verified


def test_only_the_claimant_asks_for_verification(user):
    server = ServerFactory()

    with pytest.raises(DomainError) as error:
        services.request_verification(server=server, user=user)
    assert error.value.status == 403


# Owner edits


def test_owner_of_a_modrinth_server_writes_in_ukrainian_and_picks_a_pack(user):
    server = ServerFactory(owner=user, is_verified=True)
    client = APIClient()
    client.force_login(user)
    pack = PackFactory(author=user)

    response = client.patch(
        f"/api/v1/servers/{server.slug}",
        {
            "description_uk_md": "Сервер **для друзів**",
            "discord_url": "https://discord.gg/abc",
            "required_pack": pack.slug,
            "name": "Нова назва",  # not theirs to change on a Modrinth server
        },
        format="json",
    )

    assert response.status_code == 200
    data = response.json()
    assert "<strong>для друзів</strong>" in data["description_uk_html"]
    assert data["required_pack"]["slug"] == pack.slug
    assert data["content_kind"] == "modded"
    assert data["name"] == server.name


def test_a_pack_for_joining_must_be_mine_or_from_modrinth(user):
    server = ServerFactory(owned=True, owner=user)
    strangers = PackFactory()
    modrinth = PackFactory(origin=Origin.MODRINTH)

    with pytest.raises(DomainError) as error:
        services.update_server(server=server, user=user, data={"required_pack": strangers.slug})
    assert error.value.code == "pack_not_found"
    services.update_server(server=server, user=user, data={"required_pack": modrinth.slug})
    server.refresh_from_db()
    assert server.required_pack == modrinth


def test_owner_of_their_own_server_changes_its_facts(user):
    server = ServerFactory(owned=True, owner=user)

    services.update_server(
        server=server,
        user=user,
        data={"name": "Січ", "languages": ["uk"], "country": "ua", "supported_versions": ["26.1"]},
    )

    server.refresh_from_db()
    assert (server.name, server.country, server.supported_versions) == ("Січ", "UA", ["26.1"])


def test_others_cannot_edit_and_modrinth_servers_are_not_deleted(user):
    server = ServerFactory(owner=user, is_verified=True)
    stranger = UserFactory()

    with pytest.raises(DomainError):
        services.update_server(server=server, user=stranger, data={"summary": "x"})
    with pytest.raises(DomainError) as error:
        services.delete_server(server=server, user=user)
    assert error.value.status == 403
    own = ServerFactory(owned=True, owner=user)
    services.delete_server(server=own, user=user)
    assert not Server.objects.filter(pk=own.pk).exists()


# Catalog


def test_catalog_lists_modrinth_and_proved_servers_only(api_client):
    ServerFactory(slug="modrinth")
    ServerFactory(slug="proved", owned=True)
    ServerFactory(slug="waiting", source=Source.OWNER, external_id="w:1", is_verified=False)
    ServerFactory(slug="hidden", is_hidden=True)

    assert sorted(slugs(api_client.get("/api/v1/servers", {"all": "1"}))) == ["modrinth", "proved"]


def test_ukrainian_is_the_default_language_once_there_are_enough(api_client):
    for n in range(5):
        ServerFactory(slug=f"uk-{n}", languages=["uk"])
    ServerFactory(slug="en", languages=["en"])

    assert "en" not in slugs(api_client.get("/api/v1/servers"))
    assert "en" in slugs(api_client.get("/api/v1/servers", {"all": "1"}))
    assert slugs(api_client.get("/api/v1/servers", {"language": "en"})) == ["en"]
    assert "en" in slugs(api_client.get("/api/v1/servers", {"language": ""}))


def test_few_ukrainian_servers_mean_no_default_filter(api_client):
    ServerFactory(slug="uk", languages=["uk"])
    ServerFactory(slug="en", languages=["en"])

    assert sorted(slugs(api_client.get("/api/v1/servers"))) == ["en", "uk"]


def test_filters(api_client):
    pack = PackFactory(origin=Origin.MODRINTH, game_version="1.20.1", loader="forge")
    ServerFactory(
        slug="ua-vanilla", country="UA", supported_versions=["1.21.1"], categories=["smp"]
    )
    ServerFactory(
        slug="pl-modded",
        country="PL",
        content_kind=ContentKind.MODDED,
        required_pack=pack,
        supported_versions=[],
        recommended_version="",
        categories=["pvp"],
    )

    def get(**params):
        return sorted(slugs(api_client.get("/api/v1/servers", {"all": "1", **params})))

    assert get(country="ua") == ["ua-vanilla"]
    assert get(kind="modded") == ["pl-modded"]
    assert get(version="1.20.1") == ["pl-modded"]
    assert get(version="1.21.1") == ["ua-vanilla"]
    assert get(category="pvp,creative") == ["pl-modded"]


def test_online_filter_and_sort_use_fresh_snapshots(api_client):
    busy = ServerFactory(slug="busy", name="Busy")
    quiet = ServerFactory(slug="quiet")
    ServerFactory(slug="silent")
    SnapshotFactory(server=busy, players_online=40)
    SnapshotFactory(server=quiet, players_online=3)
    live.store({busy.pk: online(40), quiet.pk: online(3)})

    assert slugs(api_client.get("/api/v1/servers", {"all": "1", "sort": "online"}))[:2] == [
        "busy",
        "quiet",
    ]
    assert sorted(slugs(api_client.get("/api/v1/servers", {"all": "1", "online": "true"}))) == [
        "busy",
        "quiet",
    ]
    card = api_client.get("/api/v1/servers", {"all": "1", "q": "busy"}).json()["results"][0]
    assert card["live"]["players_online"] == 40
    assert card["source"]["name"] == "Modrinth"


def test_catalog_has_no_n_plus_one(api_client, django_assert_max_num_queries):
    for _ in range(8):
        ServerFactory()

    with django_assert_max_num_queries(5):
        response = api_client.get("/api/v1/servers", {"all": "1"})
    assert response.json()["count"] == 8


def test_waiting_server_is_visible_to_its_claimant_only(api_client, user):
    server = ServerFactory(source=Source.OWNER, external_id="w:1", is_verified=False, claimant=user)
    mine = APIClient()
    mine.force_login(user)

    assert api_client.get(f"/api/v1/servers/{server.slug}").status_code == 404
    assert mine.get(f"/api/v1/servers/{server.slug}").status_code == 200
    assert api_client.get("/api/v1/me/servers").status_code == 401
    assert mine.get("/api/v1/me/servers").json()["count"] == 1


# «Щоб зайти»


def test_join_of_a_vanilla_server_names_the_version(api_client, game_versions):
    server = ServerFactory(supported_versions=["1.21.1", "1.21"], recommended_version="1.21.1")

    api_client.cookies["bc_game"] = "1.21.1:fabric"
    fits = api_client.get(f"/api/v1/servers/{server.slug}/join").json()
    api_client.cookies["bc_game"] = "26.1:fabric"
    old = api_client.get(f"/api/v1/servers/{server.slug}/join").json()

    assert (fits["kind"], fits["recommended_version"], fits["pack"]) == ("vanilla", "1.21.1", None)
    assert (fits["fits_my_game"], old["fits_my_game"]) == (True, False)


def test_join_of_a_modded_server_offers_the_pack(api_client, game_versions):
    pack = PackFactory(origin=Origin.MODRINTH, game_version="1.21.1", loader="neoforge")
    server = ServerFactory(content_kind=ContentKind.MODDED, required_pack=pack)
    waiting = ServerFactory(content_kind=ContentKind.MODDED, modpack_project_id="X")

    api_client.cookies["bc_game"] = "1.21.1:fabric"
    data = api_client.get(f"/api/v1/servers/{server.slug}/join").json()
    pending = api_client.get(f"/api/v1/servers/{waiting.slug}/join").json()

    assert data["pack"]["slug"] == pack.slug
    assert (data["versions"], data["fits_my_game"]) == (["1.21.1"], False)
    assert (pending["pack"], pending["pack_pending"]) == (None, True)


# Stats and IP


def test_copy_ip_counts(api_client):
    server = ServerFactory()

    response = api_client.post(f"/api/v1/servers/{server.slug}/copy-ip")

    assert response.json()["ip_copies_count"] == 1


def test_stats_without_pings(api_client):
    server = ServerFactory()

    data = api_client.get(f"/api/v1/servers/{server.slug}/stats").json()

    assert (data["uptime_percent"], data["points"]) == (None, [])


def test_pinged_servers_are_the_listed_and_the_waiting_ones(user):
    ServerFactory()
    ServerFactory(owned=True)
    ServerFactory(source=Source.OWNER, external_id="w:1", claimant=user, claimed_at=timezone.now())
    ServerFactory(source=Source.OWNER, external_id="w:2")  # nobody claims it any more
    old = timezone.now() - timedelta(days=8)
    ServerFactory(source=Source.OWNER, external_id="w:3", claimant=user, claimed_at=old)
    ServerFactory(is_hidden=True)

    assert services.pinged().count() == 3


def test_cleanup_keeps_a_month_of_snapshots():
    from datetime import timedelta

    from django.utils import timezone

    server = ServerFactory()
    SnapshotFactory(server=server, ts=timezone.now() - timedelta(days=40))
    SnapshotFactory(server=server)

    assert services.cleanup_snapshots() == 1
    assert server.snapshots.count() == 1


def test_meta_lists_server_languages_and_countries(api_client):
    ServerFactory(languages=["uk", "en"], country="UA")
    ServerFactory(languages=["pl"], country="")

    data = api_client.get("/api/v1/meta").json()

    assert data["server_languages"] == ["en", "pl", "uk"]
    assert data["server_countries"] == ["UA"]


def test_ping_result_dataclass_defaults():
    assert PingResult(is_online=False).players_online == 0


def test_meta_names_server_languages_countries_and_categories(api_client):
    ServerFactory(languages=["uk", "en"], country="UA", categories=["smp"])

    data = api_client.get("/api/v1/meta").json()

    assert (data["server_languages"], data["server_countries"]) == (["en", "uk"], ["UA"])
    assert data["server_default_language"] == ""  # fewer than five Ukrainian-speaking
    smp = next(c for c in data["server_categories"] if c["slug"] == "smp")
    assert (smp["name"], smp["header_name"]) == ("SMP", "Спільнота")


# Review fixes: codes per player, packs anyone can take, my servers


def test_another_claim_does_not_change_my_code(user, monkeypatch):
    server = ServerFactory()
    services._claim(server, user)
    griefer = UserFactory()
    services._claim(server, griefer)
    code = services.claim_code(server.pk, user.pk)
    monkeypatch.setattr(services.clients, "ping", fake_probe({server.java_host: online(motd=code)}))

    assert code != services.claim_code(server.pk, griefer.pk)
    assert services.verify(server_id=server.pk, user_id=griefer.pk) == "missing"
    assert services.verify(server_id=server.pk, user_id=user.pk) == "verified"
    server.refresh_from_db()
    assert (server.owner, server.is_verified) == (user, True)


def test_the_code_is_shown_only_to_the_claimant(user):
    server = ServerFactory(claimant=user, claimed_at=timezone.now())
    mine, other = APIClient(), APIClient()
    mine.force_login(user)
    other.force_login(UserFactory())

    assert mine.get(f"/api/v1/servers/{server.slug}").json()["verify_code"] == (
        services.claim_code(server.pk, user.pk)
    )
    assert other.get(f"/api/v1/servers/{server.slug}").json()["verify_code"] is None


def test_owner_picks_only_a_pack_everyone_can_take(user):
    server = ServerFactory(owner=user, is_verified=True)
    by_link = PackFactory(author=user, visibility="link")
    public = PackFactory(author=user)

    with pytest.raises(DomainError):
        services.update_server(server=server, user=user, data={"required_pack": by_link.slug})
    services.update_server(server=server, user=user, data={"required_pack": public.slug})

    server.refresh_from_db()
    assert (server.required_pack, server.pack_chosen_by_owner) == (public, True)


def test_a_pack_that_stopped_being_public_is_not_offered(api_client, user):
    pack = PackFactory(author=user)
    server = ServerFactory(content_kind=ContentKind.MODDED, required_pack=pack)
    pack.visibility = "link"
    pack.save()

    join = api_client.get(f"/api/v1/servers/{server.slug}/join").json()
    detail = api_client.get(f"/api/v1/servers/{server.slug}").json()

    assert (join["pack"], detail["required_pack"]) == (None, None)


def test_my_servers_without_n_plus_one(user, django_assert_max_num_queries):
    client = APIClient()
    client.force_login(user)
    for _ in range(5):
        ServerFactory(owner=user, is_verified=True, required_pack=PackFactory())

    with django_assert_max_num_queries(8):
        response = client.get("/api/v1/me/servers")
    assert response.json()["count"] == 5
