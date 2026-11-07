import httpx
import pytest
import respx

from apps.sources.clients.loaders import (
    FABRIC_META,
    FORGE_PROMOTIONS,
    NEOFORGE_VERSIONS,
    QUILT_META,
    LoaderClient,
    LoaderMetaError,
    neoforge_prefix,
)


@pytest.fixture
def client():
    with LoaderClient(sleep=lambda delay: None) as client:
        yield client


def builds(*versions: tuple[str, bool | None]) -> list[dict]:
    rows = []
    for version, stable in versions:
        loader = {"separator": ".", "build": 1, "maven": "x", "version": version}
        if stable is not None:
            loader["stable"] = stable
        rows.append({"loader": loader, "intermediary": {}})
    return rows


@respx.mock
def test_fabric_takes_the_first_stable_build(client):
    respx.get(FABRIC_META.format(game="26.3")).respond(
        json=builds(("0.18.0", False), ("0.17.2", True), ("0.17.1", True))
    )

    assert client.latest("fabric", "26.3") == "0.17.2"


@respx.mock
def test_quilt_skips_pre_releases(client):
    respx.get(QUILT_META.format(game="1.21.1")).respond(
        json=builds(("0.30.0-beta.2", None), ("0.24.0", None), ("0.29.2", None), ("0.3.1", None))
    )

    assert client.latest("quilt", "1.21.1") == "0.29.2"


@respx.mock
def test_unknown_game_versions_have_no_build(client):
    respx.get(FABRIC_META.format(game="1.8.9")).respond(json=[])
    respx.get(QUILT_META.format(game="1.8.9")).respond(404)

    assert client.latest("fabric", "1.8.9") is None
    assert client.latest("quilt", "1.8.9") is None
    assert client.latest("vanilla", "1.8.9") is None


@respx.mock
def test_forge_prefers_the_recommended_build_and_asks_once(client):
    route = respx.get(FORGE_PROMOTIONS).respond(
        json={
            "promos": {
                "1.20.1-recommended": "47.3.0",
                "1.20.1-latest": "47.4.10",
                "1.21.1-latest": "52.1.0",
            }
        }
    )

    assert client.latest("forge", "1.20.1") == "47.3.0"
    assert client.latest("forge", "1.21.1") == "52.1.0"
    assert client.latest("forge", "26.3") is None
    assert route.call_count == 1


@pytest.mark.parametrize(
    ("game_version", "prefix"),
    [("1.21.1", "21.1."), ("1.21", "21.0."), ("1.20.4", "20.4."), ("26.1", "26.1.0."),
     ("26.1.2", "26.1.2.")],
)  # fmt: skip
def test_neoforge_prefix(game_version, prefix):
    assert neoforge_prefix(game_version) == prefix


@respx.mock
def test_neoforge_takes_the_newest_stable_build_of_the_line(client):
    respx.get(NEOFORGE_VERSIONS).respond(
        json={
            "isSnapshot": False,
            "versions": ["21.1.9", "21.1.200", "21.1.77", "21.10.1", "26.1.0.5-beta"],
        }
    )

    assert client.latest("neoforge", "1.21.1") == "21.1.200"
    assert client.latest("neoforge", "26.1") == "26.1.0.5-beta"
    assert client.latest("neoforge", "1.20.1") is None


@respx.mock
def test_server_errors_are_retried_then_skipped(client):
    route = respx.get(FABRIC_META.format(game="26.3")).mock(
        side_effect=[httpx.Response(503), httpx.ConnectError("down"), httpx.Response(502)]
    )
    respx.get(QUILT_META.format(game="26.3")).respond(json=builds(("0.29.2", None)))
    respx.get(FORGE_PROMOTIONS).respond(json={"promos": {}})
    respx.get(NEOFORGE_VERSIONS).respond(json={"versions": ["26.3.0.1"]})

    with pytest.raises(LoaderMetaError):
        client.latest("fabric", "26.3")
    route.side_effect = [httpx.Response(503)] * 3

    assert client.latest_many(["26.3"]) == {
        ("quilt", "26.3"): "0.29.2",
        ("neoforge", "26.3"): "26.3.0.1",
    }
