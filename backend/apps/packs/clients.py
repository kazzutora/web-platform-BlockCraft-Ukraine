"""Latest stable builds of mod loaders. Call it only from Celery tasks."""

import logging
import time
from collections.abc import Callable, Iterable
from typing import Any, Self

import httpx
from django.conf import settings
from pydantic import TypeAdapter

from apps.core.versions import version_key

from .choices import PackLoader
from .schemas import ForgePromotions, LoaderEntry, MavenVersions

logger = logging.getLogger(__name__)

FABRIC_META = "https://meta.fabricmc.net/v2/versions/loader/{game}"
QUILT_META = "https://meta.quiltmc.org/v3/versions/loader/{game}"
FORGE_PROMOTIONS = "https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json"
NEOFORGE_VERSIONS = "https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/neoforge"

_entries = TypeAdapter(list[LoaderEntry])


class LoaderMetaError(Exception):
    """A loader site did not answer after all retries."""


def neoforge_prefix(game_version: str) -> str:
    """NeoForge builds carry the game version: 1.21.1 → 21.1.x, 1.21 → 21.0.x, 26.1 → 26.1.0.x."""
    parts = game_version.split(".")
    if parts[0] == "1":
        return f"{parts[1]}.{parts[2] if len(parts) > 2 else 0}."
    return f"{parts[0]}.{parts[1]}.{parts[2] if len(parts) > 2 else 0}."


def _is_stable(version: str) -> bool:
    return "-" not in version and "+" not in version


class LoaderClient:
    def __init__(
        self,
        *,
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 2,
        backoff: float = 0.5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = httpx.Client(
            timeout=10.0,
            headers={"User-Agent": settings.MODRINTH_USER_AGENT},
            transport=transport,
            follow_redirects=True,
        )
        self._max_retries = max_retries
        self._backoff = backoff
        self._sleep = sleep
        self._forge: dict[str, str] | None = None
        self._neoforge: list[str] | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._client.close()

    def _get(self, url: str) -> Any | None:
        """JSON of `url`; None when the site does not know it (404, 400)."""
        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.get(url)
            except httpx.TransportError as error:
                if attempt == self._max_retries:
                    raise LoaderMetaError(f"GET {url}: {error}") from error
            else:
                if response.status_code in (400, 404):
                    return None
                if response.status_code < 500:
                    response.raise_for_status()
                    return response.json()
                if attempt == self._max_retries:
                    raise LoaderMetaError(f"GET {url}: HTTP {response.status_code}")
            self._sleep(self._backoff * 2**attempt)
        return None  # pragma: no cover

    def _fabric_like(self, url: str, *, stable_flag: bool) -> str | None:
        data = self._get(url)
        if not data:
            return None
        # Quilt lists builds in no particular order: take the highest stable number
        stable = [
            entry.loader.version
            for entry in _entries.validate_python(data)
            if (entry.loader.stable if stable_flag else _is_stable(entry.loader.version))
            is not False
        ]
        return max(stable, key=version_key, default=None)

    def _forge_version(self, game_version: str) -> str | None:
        if self._forge is None:
            data = self._get(FORGE_PROMOTIONS)
            self._forge = ForgePromotions.model_validate(data or {}).promos
        return self._forge.get(f"{game_version}-recommended") or self._forge.get(
            f"{game_version}-latest"
        )

    def _neoforge_version(self, game_version: str) -> str | None:
        if self._neoforge is None:
            data = self._get(NEOFORGE_VERSIONS)
            self._neoforge = MavenVersions.model_validate(data or {}).versions
        prefix = neoforge_prefix(game_version)
        builds = [version for version in self._neoforge if version.startswith(prefix)]
        stable = [version for version in builds if _is_stable(version)]
        return max(stable or builds, key=version_key, default=None)

    def latest(self, loader: str, game_version: str) -> str | None:
        """The build a fresh pack should use; None when the loader has none for that version."""
        if loader == PackLoader.FABRIC:
            return self._fabric_like(FABRIC_META.format(game=game_version), stable_flag=True)
        if loader == PackLoader.QUILT:
            return self._fabric_like(QUILT_META.format(game=game_version), stable_flag=False)
        if loader == PackLoader.FORGE:
            return self._forge_version(game_version)
        if loader == PackLoader.NEOFORGE:
            return self._neoforge_version(game_version)
        return None

    def latest_many(self, game_versions: Iterable[str]) -> dict[tuple[str, str], str]:
        found: dict[tuple[str, str], str] = {}
        for game_version in game_versions:
            for loader in PackLoader.values:
                try:
                    version = self.latest(loader, game_version)
                except LoaderMetaError:
                    logger.warning("No %s builds for %s", loader, game_version, exc_info=True)
                    continue
                if version:
                    found[(loader, game_version)] = version
        return found
