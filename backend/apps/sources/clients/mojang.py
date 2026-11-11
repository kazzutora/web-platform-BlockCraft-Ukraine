"""Mojang API: nickname → UUID → profile → skin texture (docs/sources.md, «Mojang»).

Called from a player's request, so the domain wraps it in a cache (skins.mojang.lookup).
"""

import base64
import json
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from ..schemas.mojang import MojangProfile, MojangProfileId, TexturesPayload
from .base import BaseClient, SourceError, SourceNotFoundError, SourceRateLimitedError

API_URL = "https://api.mojang.com"
SESSION_URL = "https://sessionserver.mojang.com"
TEXTURE_HOSTS = {"textures.minecraft.net"}


class MojangError(SourceError):
    """Mojang did not answer usefully after the retries."""


class MojangNotFoundError(MojangError, SourceNotFoundError):
    pass


class MojangRateLimitedError(MojangError, SourceRateLimitedError):
    pass


@dataclass(frozen=True)
class PlayerSkin:
    nickname: str
    uuid: str
    #: None when the player uses a default skin
    model: str | None
    texture_png: bytes | None
    #: https://textures.minecraft.net/texture/<id>; empty for a default skin
    texture_url: str = ""


class MojangClient(BaseClient):
    name = "Mojang"
    # A player waits for the answer: one quick retry, no waiting on 429
    timeout = 5.0
    max_retries = 1
    backoff = 0.3
    wait_on_429 = False
    error = MojangError
    not_found_error = MojangNotFoundError
    rate_limited_error = MojangRateLimitedError

    def _get(self, url: str) -> httpx.Response | None:
        """The response, or None when Mojang says «no such player» (204/404)."""
        try:
            response = self.request("GET", url)
        except MojangNotFoundError:
            return None
        return None if response.status_code == 204 else response

    def player_skin(self, nickname: str) -> PlayerSkin | None:
        response = self._get(f"{API_URL}/users/profiles/minecraft/{nickname}")
        if response is None:
            return None
        player = self.parse(MojangProfileId, self.json_of(response))

        response = self._get(f"{SESSION_URL}/session/minecraft/profile/{player.id}")
        if response is None:
            return None
        profile = self.parse(MojangProfile, self.json_of(response))
        encoded = next((p.value for p in profile.properties if p.name == "textures"), None)
        skin = self.parse(TexturesPayload, _decode(encoded)).textures.SKIN if encoded else None
        if skin is None:
            return PlayerSkin(nickname=profile.name, uuid=profile.id, model=None, texture_png=None)

        url = texture_https(skin.url)
        return PlayerSkin(
            nickname=profile.name,
            uuid=profile.id,
            model="slim" if skin.metadata.model == "slim" else "classic",
            texture_png=self.texture(url),
            texture_url=url,
        )

    def texture(self, url: str) -> bytes:
        """A skin PNG from textures.minecraft.net (MineSkin points there too)."""
        response = self._get(texture_https(url))
        if response is None:
            raise MojangError("texture is gone")
        return response.content


def texture_https(url: str) -> str:
    """Only textures.minecraft.net, always over HTTPS."""
    parsed = urlparse(url)
    if parsed.hostname not in TEXTURE_HOSTS:
        raise MojangError(f"unexpected texture host {parsed.hostname}")
    return parsed._replace(scheme="https").geturl()


def _decode(encoded: str) -> object:
    try:
        return json.loads(base64.b64decode(encoded))
    except ValueError as error:
        raise MojangError("textures property is not base64 JSON") from error
