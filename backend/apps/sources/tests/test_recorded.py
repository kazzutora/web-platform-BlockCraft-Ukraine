"""Contract tests: every client reads the real answers recorded in R1.2 (docs/sources.md)."""

import base64

import pytest
import respx

from apps.sources.clients import loaders, mineskin, modrinth, modrinth_v3, mojang
from apps.sources.clients.base import SourceSchemaError
from apps.sources.schemas.modrinth_v3 import ModpackContent, VanillaContent

from .recorded import load


def quiet(cls, **kwargs):
    return cls(user_agent="blockcraft-tests/2.0", sleep=lambda seconds: None, **kwargs)


# --- Modrinth v2 ----------------------------------------------------------------------------


@respx.mock
@pytest.mark.parametrize("kind", ["mod", "shader", "resourcepack", "datapack", "modpack"])
def test_modrinth_search_reads_every_project_type(kind):
    respx.get(f"{modrinth.BASE_URL}/search").respond(json=load("modrinth", f"search_{kind}"))

    with quiet(modrinth.ModrinthClient) as client:
        page = client.search(project_type=kind, game_versions=["1.21.1"])

    assert page.hits and page.total_hits > len(page.hits)
    assert all(hit.project_id and hit.slug for hit in page.hits)


@respx.mock
def test_datapacks_come_with_the_mod_project_type():
    respx.get(f"{modrinth.BASE_URL}/search").respond(json=load("modrinth", "search_datapack"))

    with quiet(modrinth.ModrinthClient) as client:
        hits = client.search(project_type="datapack").hits

    assert {hit.project_type for hit in hits} == {"mod"}


@respx.mock
@pytest.mark.parametrize("name", ["project_sodium", "project_modpack"])
def test_modrinth_project(name):
    data = load("modrinth", name)
    respx.get(f"{modrinth.BASE_URL}/project/{data['slug']}").respond(json=data)

    with quiet(modrinth.ModrinthClient) as client:
        project = client.get_project(data["slug"])

    assert project.id == data["id"]
    assert project.gallery or project.icon_url


@respx.mock
def test_modrinth_unknown_project_is_404_with_an_empty_body():
    respx.get(f"{modrinth.BASE_URL}/project/nope").respond(404, content=b"")

    with quiet(modrinth.ModrinthClient) as client, pytest.raises(modrinth.ModrinthNotFoundError):
        client.get_project("nope")


@respx.mock
def test_modrinth_projects_by_ids():
    respx.get(f"{modrinth.BASE_URL}/projects").respond(json=load("modrinth", "projects_by_ids"))

    with quiet(modrinth.ModrinthClient) as client:
        projects = client.get_projects(["AANobbMI", "YL57xq9U"])

    assert [project.slug for project in projects] == ["sodium", "iris"]


@respx.mock
@pytest.mark.parametrize(
    ("name", "project"),
    [
        ("project_versions_sodium", "AANobbMI"),
        ("project_versions_sodium_extra", "sodium-extra"),
        ("project_versions_complementary", "complementary-reimagined"),
        ("project_versions_modpack", "fabulously-optimized"),
    ],
)
def test_modrinth_versions_have_a_primary_file_on_the_cdn(name, project):
    respx.get(f"{modrinth.BASE_URL}/project/{project}/version").respond(json=load("modrinth", name))

    with quiet(modrinth.ModrinthClient) as client:
        versions = client.get_versions(project, game_versions=["1.21.1"])

    assert versions
    for version in versions:
        file = version.primary_file
        assert file is not None and file.url.startswith(f"https://{modrinth.CDN_HOST}/")
        assert set(file.hashes) >= {"sha1", "sha512"}


@respx.mock
def test_sodium_extra_requires_sodium_without_a_version_id():
    respx.get(f"{modrinth.BASE_URL}/project/sodium-extra/version").respond(
        json=load("modrinth", "project_versions_sodium_extra")
    )

    with quiet(modrinth.ModrinthClient) as client:
        dependencies = client.get_versions("sodium-extra")[0].dependencies

    required = [d for d in dependencies if d.dependency_type == "required"]
    assert [(d.project_id, d.version_id) for d in required] == [("AANobbMI", None)]


@respx.mock
def test_modrinth_tags():
    respx.get(f"{modrinth.BASE_URL}/tag/game_version").respond(
        json=load("modrinth", "tag_game_version")
    )
    respx.get(f"{modrinth.BASE_URL}/tag/category").respond(json=load("modrinth", "tag_category"))

    with quiet(modrinth.ModrinthClient) as client:
        versions = client.get_game_versions()
        categories = client.get_categories()

    releases = [v for v in versions if v.version_type == "release"]
    assert len(versions) == 922 and len(releases) == 103
    assert {"potato", "low", "medium", "high"} <= {
        c.name for c in categories if c.header == "performance impact"
    }


# --- Modrinth v3: servers -------------------------------------------------------------------


@respx.mock
@pytest.mark.parametrize("name", ["search_servers", "search_servers_uk", "search_servers_vanilla"])
def test_v3_server_search(name):
    route = respx.get(f"{modrinth_v3.BASE_URL}/search").respond(json=load("modrinth_v3", name))

    with quiet(modrinth_v3.ModrinthV3Client) as client:
        page = client.search_servers(language="uk", content_kind="vanilla", limit=3)

    assert page.hits and page.total_hits >= len(page.hits)
    facets = route.calls.last.request.url.params["facets"]
    assert '"project_types:minecraft_java_server"' in facets
    assert '"minecraft_server.languages:uk"' in facets
    assert '"minecraft_java_server.content.kind:vanilla"' in facets


@respx.mock
@pytest.mark.parametrize(
    ("name", "kind", "own_pack"),
    [
        ("project_server_1", ModpackContent, True),
        ("project_server_2", ModpackContent, True),
        ("project_server_3", ModpackContent, True),
        ("project_server_uk", ModpackContent, True),
        ("project_server_external_pack", ModpackContent, False),
        ("project_server_vanilla", VanillaContent, False),
    ],
)
def test_v3_server_content_kinds(name, kind, own_pack):
    data = load("modrinth_v3", name)
    respx.get(f"{modrinth_v3.BASE_URL}/project/{data['id']}").respond(json=data)

    with quiet(modrinth_v3.ModrinthV3Client) as client:
        server = client.get_server(data["id"])

    assert server.minecraft_java_server.address
    assert isinstance(server.minecraft_java_server.content, kind)
    assert server.has_own_pack is own_pack


@respx.mock
def test_v3_vanilla_server_versions_come_from_content():
    data = load("modrinth_v3", "project_server_vanilla")
    respx.get(f"{modrinth_v3.BASE_URL}/project/{data['id']}").respond(json=data)

    with quiet(modrinth_v3.ModrinthV3Client) as client:
        content = client.get_server(data["id"]).minecraft_java_server.content

    assert isinstance(content, VanillaContent)
    assert content.recommended_game_version == "26.2"


@respx.mock
def test_v3_unknown_content_kind_is_a_schema_error():
    data = load("modrinth_v3", "project_server_vanilla")
    data["minecraft_java_server"]["content"] = {"kind": "plugins"}
    respx.get(f"{modrinth_v3.BASE_URL}/project/{data['id']}").respond(json=data)

    with quiet(modrinth_v3.ModrinthV3Client) as client, pytest.raises(SourceSchemaError):
        client.get_server(data["id"])


# --- MineSkin -------------------------------------------------------------------------------


@respx.mock
def test_mineskin_gallery_pages_with_a_cursor(settings):
    settings.MINESKIN_API_KEY = ""
    first, second = load("mineskin", "skins_list"), load("mineskin", "skins_list_next")
    route = respx.get(f"{mineskin.BASE_URL}/v2/skins")
    route.side_effect = [respx.MockResponse(json=first), respx.MockResponse(json=second)]

    with quiet(mineskin.MineSkinClient) as client:
        page = client.list_skins(size=3)
        following = client.list_skins(after=page.next_after, size=3)

    assert len(page.skins) == 3 and page.next_after
    assert route.calls[1].request.url.params["after"] == page.next_after
    assert following.skins[0].uuid != page.skins[0].uuid
    assert "Authorization" not in route.calls[0].request.headers


@respx.mock
def test_mineskin_skin_has_a_variant_and_a_mojang_texture(settings):
    settings.MINESKIN_API_KEY = "msk_test"
    data = load("mineskin", "skin")
    route = respx.get(f"{mineskin.BASE_URL}/v2/skins/{data['skin']['uuid']}").respond(json=data)

    with quiet(mineskin.MineSkinClient) as client:
        skin = client.get_skin(data["skin"]["uuid"])

    assert skin.variant in {"classic", "slim"}
    assert skin.texture.url.skin.startswith("https://textures.minecraft.net/texture/")
    assert route.calls.last.request.headers["Authorization"] == "Bearer msk_test"


@respx.mock
def test_mineskin_unknown_skin():
    respx.get(f"{mineskin.BASE_URL}/v2/skins/{'0' * 32}").respond(
        404, json=load("mineskin", "skin_not_found")
    )

    with quiet(mineskin.MineSkinClient) as client, pytest.raises(mineskin.MineSkinNotFoundError):
        client.get_skin("0" * 32)


# --- Mojang ---------------------------------------------------------------------------------


@respx.mock
def test_mojang_profile_and_session_from_the_recorded_answers():
    player, session = load("mojang", "profile_by_name"), load("mojang", "session_profile")
    respx.get(f"{mojang.API_URL}/users/profiles/minecraft/jeb_").respond(json=player)
    respx.get(f"{mojang.SESSION_URL}/session/minecraft/profile/{player['id']}").respond(
        json=session
    )
    texture = respx.route(host="textures.minecraft.net").respond(content=b"png")

    with quiet(mojang.MojangClient) as client:
        skin = client.player_skin("jeb_")

    assert skin is not None and skin.nickname == "jeb_" and skin.texture_png == b"png"
    assert texture.calls.last.request.url.scheme == "https"


@respx.mock
def test_mojang_unknown_player():
    respx.get(f"{mojang.API_URL}/users/profiles/minecraft/nobody_x").respond(
        404, json=load("mojang", "profile_by_name_not_found")
    )

    with quiet(mojang.MojangClient) as client:
        assert client.player_skin("nobody_x") is None


@respx.mock
def test_mojang_broken_textures_property():
    player, session = load("mojang", "profile_by_name"), load("mojang", "session_profile")
    session["properties"][0]["value"] = base64.b64encode(b"not json").decode()
    respx.get(f"{mojang.API_URL}/users/profiles/minecraft/jeb_").respond(json=player)
    respx.get(f"{mojang.SESSION_URL}/session/minecraft/profile/{player['id']}").respond(
        json=session
    )

    with quiet(mojang.MojangClient) as client, pytest.raises(mojang.MojangError):
        client.player_skin("jeb_")


# --- Loader meta ----------------------------------------------------------------------------


@respx.mock
def test_loader_builds_from_the_recorded_answers():
    respx.get(loaders.FABRIC_META.format(game="1.21.1")).respond(
        json=load("loaders", "fabric_loader_1.21.1")
    )
    respx.get(loaders.QUILT_META.format(game="1.21.1")).respond(
        json=load("loaders", "quilt_loader_1.21.1")
    )
    respx.get(loaders.FORGE_PROMOTIONS).respond(json=load("loaders", "forge_promotions_slim"))
    respx.get(loaders.NEOFORGE_VERSIONS).respond(json=load("loaders", "neoforge_versions"))

    with quiet(loaders.LoaderClient) as client:
        found = client.latest_many(["1.21.1"])

    assert found[("fabric", "1.21.1")] == "0.20.1"
    assert found[("neoforge", "1.21.1")] == "21.1.265"
    assert found[("forge", "1.21.1")].startswith("52.")
    # The three recorded Quilt builds are all betas: no stable build to pick
    assert ("quilt", "1.21.1") not in found
