"""Mojang API: nickname → UUID → profile → skin texture, cached (docs/tech.md, 8)."""

import base64
import logging
import re
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from io import BytesIO
from typing import Self
from urllib.parse import urlparse

import httpx
from django.core.cache import cache

from . import textures
from .schemas import MojangProfile, MojangProfileId, TexturesPayload

logger = logging.getLogger(__name__)

API_URL = "https://api.mojang.com"
SESSION_URL = "https://sessionserver.mojang.com"
TEXTURE_HOSTS = {"textures.minecraft.net"}
NICKNAME = re.compile(r"^[A-Za-z0-9_]{3,16}$")
FOUND_TTL = 10 * 60
NOT_FOUND_TTL = 2 * 60


class MojangError(Exception):
    """Mojang did not answer usefully after the retries."""


class MojangRateLimitedError(MojangError):
    pass


@dataclass(frozen=True)
class PlayerSkin:
    nickname: str
    uuid: str
    #: None when the player uses a default skin
    model: str | None
    texture_png: bytes | None


class MojangClient:
    def __init__(
        self,
        *,
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 1,
        backoff: float = 0.3,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = httpx.Client(
            timeout=5.0,
            headers={"User-Agent": "blockcraft-ua/1.0"},
            transport=transport,
            follow_redirects=False,
        )
        self._max_retries = max_retries
        self._backoff = backoff
        self._sleep = sleep

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._client.close()

    def _get(self, url: str) -> httpx.Response | None:
        """The response, or None when Mojang says «no such player» (204/404)."""
        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.get(url)
            except httpx.TransportError as error:
                if attempt == self._max_retries:
                    raise MojangError(f"GET {url}: {error}") from error
            else:
                if response.status_code in (204, 404):
                    return None
                if response.status_code == 429:
                    raise MojangRateLimitedError(f"GET {url}: rate limited")
                if response.status_code < 500:
                    response.raise_for_status()
                    return response
                if attempt == self._max_retries:
                    raise MojangError(f"GET {url}: HTTP {response.status_code}")
            self._sleep(self._backoff * 2**attempt)
        raise MojangError(f"GET {url}: retries exhausted")  # pragma: no cover

    def player_skin(self, nickname: str) -> PlayerSkin | None:
        response = self._get(f"{API_URL}/users/profiles/minecraft/{nickname}")
        if response is None:
            return None
        player = MojangProfileId.model_validate(response.json())

        response = self._get(f"{SESSION_URL}/session/minecraft/profile/{player.id}")
        if response is None:
            return None
        profile = MojangProfile.model_validate(response.json())
        encoded = next((p.value for p in profile.properties if p.name == "textures"), None)
        skin = (
            TexturesPayload.model_validate_json(base64.b64decode(encoded)).textures.SKIN
            if encoded
            else None
        )
        if skin is None:
            return PlayerSkin(nickname=profile.name, uuid=profile.id, model=None, texture_png=None)

        url = urlparse(skin.url)
        if url.hostname not in TEXTURE_HOSTS:
            raise MojangError(f"unexpected texture host {url.hostname}")
        response = self._get(url._replace(scheme="https").geturl())
        if response is None:
            raise MojangError("texture is gone")
        return PlayerSkin(
            nickname=profile.name,
            uuid=profile.id,
            model="slim" if skin.metadata.model == "slim" else "classic",
            texture_png=response.content,
        )


def _cache_key(nickname: str) -> str:
    return f"skins:mojang:{nickname.lower()}"


def lookup(
    nickname: str, *, client_factory: Callable[[], MojangClient] = MojangClient
) -> PlayerSkin | None:
    """Cached `PlayerSkin` (10 min) or None for unknown players (2 min); legacy textures → 64×64."""
    key = _cache_key(nickname)
    cached = cache.get(key)
    if cached is not None:
        return PlayerSkin(**cached) if cached else None
    with client_factory() as client:
        player = client.player_skin(nickname)
    if player is None:
        cache.set(key, {}, NOT_FOUND_TTL)
        return None
    if player.texture_png is not None:
        try:
            image, _legacy = textures.load(BytesIO(player.texture_png))
        except textures.SkinTextureError as error:
            logger.warning("Mojang texture of %s is not a skin: %s", nickname, error.code)
            raise MojangError("texture is not a skin") from error
        player = PlayerSkin(**{**asdict(player), "texture_png": textures.to_png(image)})
    cache.set(key, asdict(player), FOUND_TTL)
    return player
