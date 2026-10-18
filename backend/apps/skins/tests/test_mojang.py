import base64
import json
from io import BytesIO

import pytest
import respx
from PIL import Image

from apps.skins import mojang

from .factories import png_bytes, skin_image, skin_png

UUID = "069a79f444e94726a5befca90e38aaf5"
TEXTURE_URL = "http://textures.minecraft.net/texture/abc123"
PROFILE_URL = f"{mojang.API_URL}/users/profiles/minecraft/Mavka"
SESSION_URL = f"{mojang.SESSION_URL}/session/minecraft/profile/{UUID}"


def session_payload(*, url: str | None = TEXTURE_URL, model: str | None = "slim") -> dict:
    textures: dict = {}
    if url:
        textures["SKIN"] = {"url": url, **({"metadata": {"model": model}} if model else {})}
    value = {"profileId": UUID, "profileName": "Mavka", "textures": textures}
    return {
        "id": UUID,
        "name": "Mavka",
        "properties": [
            {"name": "textures", "value": base64.b64encode(json.dumps(value).encode()).decode()}
        ],
    }


def mock_player(*, texture: bytes | None = None, **session):
    respx.get(PROFILE_URL).respond(json={"id": UUID, "name": "Mavka"})
    respx.get(SESSION_URL).respond(json=session_payload(**session))
    return respx.get(TEXTURE_URL.replace("http://", "https://")).respond(
        content=texture or skin_png(slim=True), headers={"Content-Type": "image/png"}
    )


def lookup(client, nickname="Mavka"):
    return client.get("/api/v1/skins/lookup", {"nickname": nickname})


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(mojang.time, "sleep", lambda seconds: None)


@respx.mock
def test_found_player_comes_with_texture_and_model(api_client):
    texture = mock_player()

    body = lookup(api_client).json()

    assert body["nickname"] == "Mavka"
    assert body["uuid"] == UUID
    assert body["model"] == "slim"
    assert body["texture"].startswith("data:image/png;base64,")
    assert texture.called  # fetched over https, not the http link Mojang gives


@respx.mock
def test_answers_are_cached(api_client):
    texture = mock_player()

    lookup(api_client)
    lookup(api_client, nickname="mavka")

    assert texture.call_count == 1


@respx.mock
def test_unknown_player_is_404_and_cached(api_client):
    route = respx.get(f"{mojang.API_URL}/users/profiles/minecraft/Nobody").respond(404)

    first = lookup(api_client, nickname="Nobody")
    lookup(api_client, nickname="Nobody")

    assert first.status_code == 404
    assert first.json()["code"] == "player_not_found"
    assert route.call_count == 1


@respx.mock
def test_rate_limit_is_503_and_not_cached(api_client):
    route = respx.get(PROFILE_URL).respond(429)

    response = lookup(api_client)
    lookup(api_client)

    assert response.status_code == 503
    assert response.json()["code"] == "mojang_unavailable"
    assert route.call_count == 2


@respx.mock
def test_server_errors_are_retried_once(api_client):
    route = respx.get(PROFILE_URL).respond(502)

    assert lookup(api_client).status_code == 503
    assert route.call_count == 2


@respx.mock
def test_default_skin_has_no_texture(api_client):
    mock_player(url=None)

    body = lookup(api_client).json()

    assert (body["texture"], body["model"]) == (None, None)


@respx.mock
def test_missing_model_metadata_means_classic(api_client):
    mock_player(model=None)

    assert lookup(api_client).json()["model"] == "classic"


@respx.mock
def test_legacy_textures_are_converted(api_client):
    legacy = skin_image().crop((0, 0, 64, 32))

    mock_player(texture=png_bytes(legacy))

    data = base64.b64decode(lookup(api_client).json()["texture"].split(",", 1)[1])

    assert Image.open(BytesIO(data)).size == (64, 64)


@respx.mock
def test_textures_only_come_from_mojang(api_client):
    mock_player(url="http://evil.example.com/skin.png")

    assert lookup(api_client).status_code == 503


@pytest.mark.parametrize("nickname", ["ab", "a" * 17, "Мавка", "bad name"])
def test_invalid_nicknames_are_400(api_client, nickname):
    response = lookup(api_client, nickname=nickname)

    assert response.status_code == 400
    assert "nickname" in response.json()["fields"]
