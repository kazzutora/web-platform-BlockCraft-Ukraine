"""Minecraft vocabulary shared by profiles, mods and servers, and «Моя гра»."""

import contextlib
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote

from django.db import models


class Loader(models.TextChoices):
    FABRIC = "fabric", "Fabric"
    FORGE = "forge", "Forge"
    NEOFORGE = "neoforge", "NeoForge"
    QUILT = "quilt", "Quilt"
    VANILLA = "vanilla", "Vanilla"


class Edition(models.TextChoices):
    JAVA = "java", "Java"
    BEDROCK = "bedrock", "Bedrock"


# «Моя гра» (docs/tech.md, 10.2): the player's profile, or the guest cookie `1.21.1:fabric`
GAME_COOKIE = "bc_game"
_COOKIE = re.compile(r"^(?P<version>[0-9][0-9a-z.\-]{0,31})?:(?P<loader>[a-z]{0,16})$")


@dataclass(frozen=True)
class GameContext:
    game_version: str = ""
    loader: str = ""
    #: "profile", "cookie" or "none"
    source: str = "none"

    @property
    def is_set(self) -> bool:
        return bool(self.game_version or self.loader)


def parse_game_cookie(value: str | None) -> tuple[str, str] | None:
    """`1.21.1:fabric` → ("1.21.1", "fabric"); either part may be empty, not both.

    Only the shape is checked here; `game_context` also checks the version is supported.
    """
    match = _COOKIE.match(unquote(value or ""))
    if not match:
        return None
    version, loader = match["version"] or "", match["loader"]
    if loader and loader not in Loader.values:
        return None
    return (version, loader) if version or loader else None


def game_context(request: Any) -> GameContext:
    """The profile wins once it has a choice; until then guests and players use the cookie.

    Computed once per request: filters, serializers and the guest cache all ask for it.
    """
    holder = getattr(request, "_request", request)
    cached = getattr(holder, "_bc_game_context", None)
    if cached is None:
        cached = _game_context(request)
        with contextlib.suppress(AttributeError):
            holder._bc_game_context = cached
    return cached


def _game_context(request: Any) -> GameContext:
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        profile = getattr(user, "game_profile", None)
        if profile is not None and (profile.game_version_id or profile.loader):
            return GameContext(profile.game_version_id or "", profile.loader, "profile")
    parsed = parse_game_cookie(request.COOKIES.get(GAME_COOKIE))
    if parsed is None:
        return GameContext()
    version, loader = parsed
    if version and not _is_supported(version):
        version = ""
    if not (version or loader):
        return GameContext()
    return GameContext(version, loader, "cookie")


def _is_supported(version: str) -> bool:
    from apps.sources.models import GameVersion

    return GameVersion.objects.supported().filter(pk=version).exists()
