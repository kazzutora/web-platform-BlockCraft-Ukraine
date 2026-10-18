import json

import httpx
import pytest
import respx

from apps.mods.clients import BASE_URL, ModrinthClient, ModrinthError, ModrinthNotFoundError

from .payloads import CATEGORIES, project_payload, version_payload


@pytest.fixture
def sleeps():
    return []


@pytest.fixture
def client(sleeps):
    with ModrinthClient(user_agent="blockcraft-tests/1.0", sleep=sleeps.append) as client:
        yield client


@respx.mock
def test_search_sends_facets_and_parses_hits(client):
    route = respx.get(f"{BASE_URL}/search").respond(
        json={
            "hits": [
                {
                    "project_id": "AANobbMI",
                    "slug": "sodium",
                    "project_type": "mod",
                    "title": "Sodium",
                }
            ],
            "offset": 0,
            "limit": 100,
            "total_hits": 1,
        }
    )

    result = client.search(project_type="mod", game_versions=["26.3", "1.21.1"])

    request = route.calls.last.request
    assert request.headers["User-Agent"] == "blockcraft-tests/1.0"
    assert json.loads(request.url.params["facets"]) == [
        ["project_type:mod"],
        ["versions:26.3", "versions:1.21.1"],
    ]
    assert request.url.params["index"] == "downloads"
    assert result.hits[0].slug == "sodium"


@respx.mock
def test_projects_versions_and_categories_are_parsed(client):
    respx.get(f"{BASE_URL}/projects").respond(json=[project_payload()])
    respx.get(f"{BASE_URL}/project/AANobbMI/version").respond(json=[version_payload()])
    respx.get(f"{BASE_URL}/tag/category").respond(json=CATEGORIES)

    [project] = client.get_projects(["AANobbMI"])
    [version] = client.get_versions("AANobbMI", game_versions=["26.3"])

    assert project.license.name == "MIT License"
    assert version.primary_file.filename == "bAZQdGpg.jar"
    assert len(client.get_categories()) == 4


@respx.mock
def test_retries_after_429_using_retry_after(client, sleeps):
    route = respx.get(f"{BASE_URL}/project/sodium")
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "3"}),
        httpx.Response(200, json=project_payload()),
    ]

    project = client.get_project("sodium")

    assert project.slug == "sodium"
    assert route.call_count == 2
    assert sleeps == [3.0]


@respx.mock
def test_retries_5xx_with_backoff_then_gives_up(client, sleeps):
    route = respx.get(f"{BASE_URL}/project/sodium").respond(503)

    with pytest.raises(ModrinthError):
        client.get_project("sodium")

    assert route.call_count == 4
    assert sleeps == [0.5, 1.0, 2.0]


@respx.mock
def test_network_errors_are_retried(client, sleeps):
    route = respx.get(f"{BASE_URL}/project/sodium")
    route.side_effect = [
        httpx.ConnectTimeout("timeout"),
        httpx.Response(200, json=project_payload()),
    ]

    assert client.get_project("sodium").slug == "sodium"
    assert sleeps == [0.5]


@respx.mock
def test_not_found_is_not_retried(client):
    route = respx.get(f"{BASE_URL}/project/nope").respond(404)

    with pytest.raises(ModrinthNotFoundError):
        client.get_project("nope")
    assert route.call_count == 1


@respx.mock
def test_waits_when_rate_limit_is_almost_spent(client, sleeps):
    respx.get(f"{BASE_URL}/tag/category").respond(
        json=[], headers={"X-Ratelimit-Remaining": "1", "X-Ratelimit-Reset": "12"}
    )

    client.get_categories()

    assert sleeps == [12.0]
