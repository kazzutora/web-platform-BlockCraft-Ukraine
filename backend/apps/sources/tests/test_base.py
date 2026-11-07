import httpx
import pytest
import respx
from pydantic import BaseModel

from apps.sources.clients.base import (
    BaseClient,
    SourceError,
    SourceNotFoundError,
    SourceRateLimitedError,
    SourceSchemaError,
)

URL = "https://api.example.test/thing"


class Thing(BaseModel):
    id: str
    size: int


class ExampleClient(BaseClient):
    name = "Example"
    base_url = "https://api.example.test"


class ImpatientClient(ExampleClient):
    wait_on_429 = False


@pytest.fixture
def sleeps() -> list[float]:
    return []


@pytest.fixture
def client(sleeps):
    with ExampleClient(user_agent="blockcraft-tests/2.0", sleep=sleeps.append) as client:
        yield client


@respx.mock
def test_success_sends_the_user_agent_and_parses_the_answer(client):
    route = respx.get(URL).respond(json={"id": "a", "size": 3, "extra": "ignored"})

    thing = client.parse(Thing, client.get_json("/thing"))

    assert thing == Thing(id="a", size=3)
    assert route.calls.last.request.headers["User-Agent"] == "blockcraft-tests/2.0"


def test_default_user_agent_comes_from_settings(settings):
    settings.SOURCES_USER_AGENT = "blockcraft-ua/2.0 (contact: test@example.com)"
    with ExampleClient() as client:
        assert client._client.headers["User-Agent"] == settings.SOURCES_USER_AGENT


@respx.mock
def test_429_waits_for_retry_after_and_retries(client, sleeps):
    respx.get(URL).mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "7"}),
            httpx.Response(200, json={"id": "a", "size": 1}),
        ]
    )

    assert client.get_json("/thing") == {"id": "a", "size": 1}
    assert sleeps == [7.0]


@respx.mock
def test_429_falls_back_to_the_rate_limit_reset_header(client, sleeps):
    respx.get(URL).mock(
        side_effect=[
            httpx.Response(429, headers={"X-Ratelimit-Reset": "12"}),
            httpx.Response(200, json={}),
        ]
    )

    client.get_json("/thing")

    assert sleeps == [12.0]


@respx.mock
def test_server_errors_are_retried_with_backoff_then_fail(client, sleeps):
    route = respx.get(URL).respond(502)

    with pytest.raises(SourceError, match="HTTP 502"):
        client.get_json("/thing")

    assert route.call_count == 4
    assert sleeps == [0.5, 1.0, 2.0]


@respx.mock
def test_network_errors_are_retried(client, sleeps):
    respx.get(URL).mock(side_effect=[httpx.ConnectError("down"), httpx.Response(200, json={})])

    assert client.get_json("/thing") == {}
    assert sleeps == [0.5]


@respx.mock
def test_404_is_not_found_without_retries(client):
    route = respx.get(URL).respond(404)

    with pytest.raises(SourceNotFoundError):
        client.get_json("/thing")

    assert route.call_count == 1


@respx.mock
def test_other_client_errors_fail_at_once(client):
    route = respx.get(URL).respond(403)

    with pytest.raises(SourceError, match="HTTP 403"):
        client.get_json("/thing")

    assert route.call_count == 1


@respx.mock
def test_a_changed_answer_is_a_schema_error(client):
    respx.get(URL).respond(json={"id": "a", "size": "big"})

    with pytest.raises(SourceSchemaError, match="Example"):
        client.parse(Thing, client.get_json("/thing"))


@respx.mock
def test_a_non_json_answer_is_a_schema_error(client):
    respx.get(URL).respond(text="<html>maintenance</html>")

    with pytest.raises(SourceSchemaError, match="not JSON"):
        client.get_json("/thing")


@respx.mock
def test_waits_when_the_rate_limit_budget_is_almost_spent(client, sleeps):
    respx.get(URL).respond(
        json={}, headers={"X-Ratelimit-Remaining": "1", "X-Ratelimit-Reset": "9"}
    )

    client.get_json("/thing")

    assert sleeps == [9.0]


@respx.mock
def test_impatient_clients_raise_on_429():
    respx.get(URL).respond(429, headers={"Retry-After": "30"})

    with (
        ImpatientClient(sleep=lambda seconds: None) as client,
        pytest.raises(SourceRateLimitedError),
    ):
        client.get_json("/thing")


@respx.mock
def test_post_sends_json(client):
    route = respx.post(URL).respond(json={"ok": True})

    assert client.post_json("/thing", {"hashes": ["a"]}) == {"ok": True}
    assert route.calls.last.request.content == b'{"hashes":["a"]}'
