from datetime import timedelta
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.tests.factories import UserFactory
from apps.servers import services, status
from apps.servers.models import Server
from apps.social.models import Review

from .factories import ServerFactory, SnapshotFactory, fake_probe, online

pytestmark = pytest.mark.django_db

FORM = {
    "name": "Козацька Січ",
    "host": "play.sich.example.com",
    "edition": "java",
    "modes": ["survival", "rp"],
    "language": "uk",
    "versions_label": "1.20–1.21",
    "description": "Виживання з історією.",
    "discord_url": "https://discord.gg/sich",
}


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_login(user)
    return client


def create(client, **changes):
    return client.post("/api/v1/servers", {**FORM, **changes}, format="json")


# Adding


def test_new_server_waits_for_moderation_and_gets_a_slug(auth_client):
    response = create(auth_client)

    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["slug"] == "kozatska-sich"
    assert body["status"] == "pending"
    assert body["address"] == "play.sich.example.com"
    assert body["verify_code"].startswith("bc-")
    assert body["is_verified"] is False


def test_host_with_port_and_default_ports(auth_client):
    body = create(auth_client, host="mc.example.com:25570").json()
    assert (body["host"], body["port"], body["address"]) == (
        "mc.example.com",
        25570,
        "mc.example.com:25570",
    )

    body = create(auth_client, name="Бедрок", host="pe.example.com", edition="bedrock").json()
    assert (body["port"], body["address"]) == (19132, "pe.example.com")


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "192.168.0.10", "minecraft.local"])
def test_internal_addresses_are_rejected(auth_client, host):
    response = create(auth_client, host=host)

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_address"
    assert "host" in response.json()["fields"]


def test_the_same_address_cannot_be_added_twice(auth_client):
    create(auth_client)

    response = create(auth_client, name="Копія")

    assert response.json()["code"] == "server_exists"


def test_same_name_gets_another_slug(auth_client):
    create(auth_client)

    assert create(auth_client, host="two.example.com").json()["slug"] == "kozatska-sich-2"


def test_form_checks(auth_client):
    assert create(auth_client, modes=[]).status_code == 400
    response = create(auth_client, discord_url="https://evil.example.com/invite")
    assert "discord_url" in response.json()["fields"]


def test_guests_cannot_add_servers(api_client):
    assert create(api_client).status_code == 401


def test_added_server_is_pinged_right_away(
    auth_client, django_capture_on_commit_callbacks, monkeypatch
):
    monkeypatch.setattr(
        services.clients, "ping", fake_probe({"play.sich.example.com": online(players=30)})
    )

    with django_capture_on_commit_callbacks(execute=True):
        slug = create(auth_client).json()["slug"]

    live = auth_client.get(f"/api/v1/servers/{slug}").json()["live"]
    assert (live["is_online"], live["players_online"]) == (True, 30)


# Catalog


def test_catalog_lists_published_servers_with_live_status(api_client):
    up = ServerFactory(name="Онлайн")
    ServerFactory(name="Чекає", status=Server.Status.PENDING)
    status.store({up.pk: online(players=5)})

    results = api_client.get("/api/v1/servers").json()["results"]

    assert [s["name"] for s in results] == ["Онлайн"]
    assert results[0]["live"]["players_online"] == 5


def test_unknown_status_is_null(api_client):
    ServerFactory()

    assert api_client.get("/api/v1/servers").json()["results"][0]["live"] is None


def test_filters(api_client):
    ServerFactory(name="Анархія", modes=["anarchy"], edition="java", has_whitelist=True)
    ServerFactory(name="Обидва", modes=["survival", "pvp"], edition="both", language="multi")
    ServerFactory(name="Телефон", modes=["minigames"], edition="bedrock", versions_label="1.21")

    def names(**params):
        return {s["name"] for s in api_client.get("/api/v1/servers", params).json()["results"]}

    assert names(mode="pvp,anarchy") == {"Анархія", "Обидва"}
    assert names(edition="bedrock") == {"Обидва", "Телефон"}
    assert names(language="multi") == {"Обидва"}
    assert names(whitelist="true") == {"Анархія"}
    assert names(version="1.21") == {"Телефон"}
    assert names(q="теле") == {"Телефон"}


def test_online_filter_and_sort_use_fresh_snapshots(api_client):
    busy, quiet, stale = (
        ServerFactory(name="Людно"),
        ServerFactory(name="Тихо"),
        ServerFactory(name="Давно"),
    )
    SnapshotFactory(server=busy, players_online=80)
    SnapshotFactory(server=quiet, players_online=3)
    SnapshotFactory(server=stale, players_online=500, ts=timezone.now() - timedelta(hours=1))
    ServerFactory(name="Офлайн")

    online_names = [
        s["name"]
        for s in api_client.get("/api/v1/servers", {"online": "true", "sort": "online"}).json()[
            "results"
        ]
    ]

    assert online_names == ["Людно", "Тихо"]


def test_catalog_has_no_n_plus_one(auth_client, django_assert_max_num_queries):
    servers = ServerFactory.create_batch(10)
    status.store({s.pk: online() for s in servers})

    with django_assert_max_num_queries(4):
        response = auth_client.get("/api/v1/servers", {"sort": "online"})

    assert len(response.json()["results"]) == 10


# Page, edits, banner


def test_pending_server_is_visible_only_to_its_owner(api_client):
    server = ServerFactory(status=Server.Status.PENDING)

    assert api_client.get(f"/api/v1/servers/{server.slug}").status_code == 404
    body = client_for(server.author).get(f"/api/v1/servers/{server.slug}").json()
    assert body["is_mine"] is True


def test_verify_code_is_shown_only_to_the_owner(api_client):
    server = ServerFactory()

    assert api_client.get(f"/api/v1/servers/{server.slug}").json()["verify_code"] is None
    owner_view = client_for(server.author).get(f"/api/v1/servers/{server.slug}").json()
    assert owner_view["verify_code"] == server.verify_code


def test_moving_the_server_resets_verification():
    server = ServerFactory(is_verified=True)
    old_code = server.verify_code
    client = client_for(server.author)

    body = client.patch(
        f"/api/v1/servers/{server.slug}", {"host": "new.example.com"}, format="json"
    ).json()

    assert (body["host"], body["is_verified"]) == ("new.example.com", False)
    server.refresh_from_db()
    assert server.verify_code != old_code


def test_description_edit_keeps_verification():
    server = ServerFactory(is_verified=True)

    body = (
        client_for(server.author)
        .patch(f"/api/v1/servers/{server.slug}", {"description": "Новий опис"}, format="json")
        .json()
    )

    assert (body["description"], body["is_verified"]) == ("Новий опис", True)


def test_others_cannot_edit_or_delete():
    server = ServerFactory()
    client = client_for(UserFactory())

    assert (
        client.patch(f"/api/v1/servers/{server.slug}", {"name": "Моє"}, format="json").status_code
        == 403
    )
    assert client.delete(f"/api/v1/servers/{server.slug}").status_code == 403


def test_owner_deletes_the_server():
    author = UserFactory(published_count=1)
    server = ServerFactory(author=author)

    assert client_for(author).delete(f"/api/v1/servers/{server.slug}").status_code == 204

    author.refresh_from_db()
    assert (Server.objects.count(), author.published_count) == (0, 0)


def banner_file(size=(1600, 900), image_format="PNG"):
    buffer = BytesIO()
    Image.new("RGB", size, (40, 120, 60)).save(buffer, format=image_format)
    return SimpleUploadedFile("banner.png", buffer.getvalue(), content_type="image/png")


def test_banner_is_cropped_to_webp():
    server = ServerFactory()
    client = client_for(server.author)

    body = client.put(
        f"/api/v1/servers/{server.slug}/banner", {"banner": banner_file()}, format="multipart"
    ).json()

    assert body["banner_url"].endswith(".webp")
    server.refresh_from_db()
    with server.banner.open("rb") as file:
        assert Image.open(file).size == (1200, 300)
    assert client.delete(f"/api/v1/servers/{server.slug}/banner").json()["banner_url"] is None


def test_broken_banner_is_rejected():
    server = ServerFactory()
    upload = SimpleUploadedFile("x.png", b"not an image", content_type="image/png")

    response = client_for(server.author).put(
        f"/api/v1/servers/{server.slug}/banner", {"banner": upload}, format="multipart"
    )

    assert response.json()["code"] == "banner_invalid"


def test_copy_ip_counts_and_is_rate_limited(api_client):
    server = ServerFactory()

    first = api_client.post(f"/api/v1/servers/{server.slug}/copy-ip")
    assert first.json() == {"ip_copies_count": 1}
    for _ in range(59):
        api_client.post(f"/api/v1/servers/{server.slug}/copy-ip")
    assert api_client.post(f"/api/v1/servers/{server.slug}/copy-ip").status_code == 429


# Stats


def test_stats_for_a_day_keep_every_ping():
    server = ServerFactory()
    now = timezone.now()
    for minutes, players, is_online in [(10, 4, True), (5, 6, True), (0, 0, False)]:
        SnapshotFactory(
            server=server,
            ts=now - timedelta(minutes=minutes),
            players_online=players,
            is_online=is_online,
        )
    SnapshotFactory(server=server, ts=now - timedelta(days=2))

    body = APIClient().get(f"/api/v1/servers/{server.slug}/stats").json()

    assert [p["players"] for p in body["points"]] == [4, 6, 0]
    assert body["uptime_percent"] == pytest.approx(66.7)
    assert body["peak_players"] == 6


def test_stats_for_a_week_are_hourly_averages():
    server = ServerFactory()
    hour = timezone.now().replace(minute=30, second=0, microsecond=0) - timedelta(hours=3)
    for minutes, players in [(0, 10), (5, 20), (10, 30)]:
        SnapshotFactory(server=server, ts=hour + timedelta(minutes=minutes), players_online=players)
    SnapshotFactory(server=server, ts=hour + timedelta(hours=1), players_online=8)

    body = APIClient().get(f"/api/v1/servers/{server.slug}/stats", {"range": "7d"}).json()

    assert [p["players"] for p in body["points"]] == [20.0, 8.0]
    assert body["uptime_percent"] == 100.0


def test_stats_without_pings():
    server = ServerFactory()

    body = APIClient().get(f"/api/v1/servers/{server.slug}/stats").json()

    assert (body["points"], body["uptime_percent"]) == ([], None)


# Verification


def test_verification_finds_the_code_in_the_motd(django_capture_on_commit_callbacks, monkeypatch):
    server = ServerFactory(host="mc.example.com")
    motd = f"Козацька Січ | {server.verify_code}"
    monkeypatch.setattr(services.clients, "ping", fake_probe({"mc.example.com": online(motd=motd)}))
    client = client_for(server.author)

    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(f"/api/v1/servers/{server.slug}/verify")

    assert (response.status_code, response.json()) == (202, {"state": "checking"})
    assert client.get(f"/api/v1/servers/{server.slug}/verify").json() == {"state": "verified"}
    assert client.get(f"/api/v1/servers/{server.slug}").json()["is_verified"] is True


@pytest.mark.parametrize(
    ("results", "state"),
    [({"mc.example.com": online(motd="Просто сервер")}, "missing"), ({}, "offline")],
)
def test_verification_without_the_code(results, state):
    server = ServerFactory(host="mc.example.com")

    assert services.verify(server_id=server.pk, probe=fake_probe(results)) == state
    server.refresh_from_db()
    assert server.is_verified is False


def test_only_the_owner_verifies():
    server = ServerFactory()

    response = client_for(UserFactory()).post(f"/api/v1/servers/{server.slug}/verify")

    assert response.status_code == 403


def test_verification_state_starts_idle(api_client):
    server = ServerFactory()

    assert api_client.get(f"/api/v1/servers/{server.slug}/verify").json() == {"state": "idle"}


# Reviews


def review(client, server, stars, text=""):
    return client.put(
        "/api/v1/reviews",
        {"kind": "server", "id": server.slug, "stars": stars, "text": text},
        format="json",
    )


def test_second_review_within_30_days_updates_the_first(auth_client):
    server = ServerFactory()

    review(auth_client, server, 2, "Лагає")
    review(auth_client, server, 5, "Виправили лаги")

    assert Review.objects.count() == 1
    server.refresh_from_db()
    assert (server.rating_avg, server.rating_count) == (5, 1)


def test_owners_cannot_review_their_server():
    server = ServerFactory()

    response = review(client_for(server.author), server, 5)

    assert response.json()["code"] == "own_object"


def test_my_servers_include_every_status():
    author = UserFactory()
    ServerFactory(author=author, status=Server.Status.PENDING)
    ServerFactory(author=author)
    ServerFactory()

    results = client_for(author).get("/api/v1/me/servers").json()["results"]

    assert sorted(s["status"] for s in results) == ["pending", "published"]


def test_trusted_owner_publishes_right_away():
    trusted = UserFactory(role=User.Role.TRUSTED)

    assert create(client_for(trusted)).json()["status"] == "published"
