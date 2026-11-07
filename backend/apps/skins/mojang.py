"""Skin of a player by nickname: Mojang behind a cache (docs/tech.md, 8.4)."""

import logging
import re
from collections.abc import Callable
from dataclasses import asdict
from io import BytesIO

from django.core.cache import cache

from apps.sources.clients.base import SourceSchemaError
from apps.sources.clients.mojang import MojangClient, MojangError, PlayerSkin

from . import textures

__all__ = ["NICKNAME", "MojangError", "PlayerSkin", "lookup"]

logger = logging.getLogger(__name__)

NICKNAME = re.compile(r"^[A-Za-z0-9_]{3,16}$")
FOUND_TTL = 10 * 60
NOT_FOUND_TTL = 2 * 60


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
    try:
        with client_factory() as client:
            player = client.player_skin(nickname)
    except SourceSchemaError as error:
        # A changed Mojang answer is «unavailable» for the player, not a server error
        raise MojangError(str(error)) from error
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
