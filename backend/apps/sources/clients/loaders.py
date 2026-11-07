"""Latest stable builds of mod loaders (docs/sources.md, «Мета лоадерів»). Celery only."""

import logging
from collections.abc import Iterable
from typing import Any

from pydantic import TypeAdapter

from apps.core.game import Loader
from apps.core.versions import version_key

from ..schemas.loaders import ForgePromotions, LoaderEntry, MavenVersions
from .base import BaseClient, SourceError, SourceNotFoundError

logger = logging.getLogger(__name__)

FABRIC_META = "https://meta.fabricmc.net/v2/versions/loader/{game}"
QUILT_META = "https://meta.quiltmc.org/v3/versions/loader/{game}"
FORGE_PROMOTIONS = "https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json"
NEOFORGE_VERSIONS = "https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/neoforge"
#: Loaders a modpack can run on; vanilla has nothing to install
LOADERS = (Loader.FABRIC, Loader.FORGE, Loader.NEOFORGE, Loader.QUILT)

_entries = TypeAdapter(list[LoaderEntry])


class LoaderMetaError(SourceError):
    """A loader site did not answer after all retries."""


class LoaderUnknownError(LoaderMetaError, SourceNotFoundError):
    pass


def neoforge_prefix(game_version: str) -> str:
    """NeoForge builds carry the game version: 1.21.1 → 21.1.x, 1.21 → 21.0.x, 26.1 → 26.1.0.x."""
    parts = game_version.split(".")
    if parts[0] == "1":
        return f"{parts[1]}.{parts[2] if len(parts) > 2 else 0}."
    return f"{parts[0]}.{parts[1]}.{parts[2] if len(parts) > 2 else 0}."


def _is_stable(version: str) -> bool:
    return "-" not in version and "+" not in version


class LoaderClient(BaseClient):
    name = "Loader meta"
    max_retries = 2
    follow_redirects = True
    # Fabric answers 400 for a game version it does not know
    not_found_statuses = frozenset({400, 404})
    error = LoaderMetaError
    not_found_error = LoaderUnknownError

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._forge: dict[str, str] | None = None
        self._neoforge: list[str] | None = None

    def _get(self, url: str) -> Any | None:
        """JSON of `url`; None when the site does not know it."""
        try:
            return self.get_json(url)
        except LoaderUnknownError:
            return None

    def _fabric_like(self, url: str, *, stable_flag: bool) -> str | None:
        data = self._get(url)
        if not data:
            return None
        # Quilt lists builds in no particular order: take the highest stable number
        stable = [
            entry.loader.version
            for entry in self.parse(_entries, data)
            if (entry.loader.stable if stable_flag else _is_stable(entry.loader.version))
            is not False
        ]
        return max(stable, key=version_key, default=None)

    def _forge_version(self, game_version: str) -> str | None:
        if self._forge is None:
            data = self._get(FORGE_PROMOTIONS)
            self._forge = self.parse(ForgePromotions, data or {}).promos
        return self._forge.get(f"{game_version}-recommended") or self._forge.get(
            f"{game_version}-latest"
        )

    def _neoforge_version(self, game_version: str) -> str | None:
        if self._neoforge is None:
            data = self._get(NEOFORGE_VERSIONS)
            self._neoforge = self.parse(MavenVersions, data or {}).versions
        prefix = neoforge_prefix(game_version)
        builds = [version for version in self._neoforge if version.startswith(prefix)]
        stable = [version for version in builds if _is_stable(version)]
        return max(stable or builds, key=version_key, default=None)

    def latest(self, loader: str, game_version: str) -> str | None:
        """The build a fresh pack should use; None when the loader has none for that version."""
        if loader == Loader.FABRIC:
            return self._fabric_like(FABRIC_META.format(game=game_version), stable_flag=True)
        if loader == Loader.QUILT:
            return self._fabric_like(QUILT_META.format(game=game_version), stable_flag=False)
        if loader == Loader.FORGE:
            return self._forge_version(game_version)
        if loader == Loader.NEOFORGE:
            return self._neoforge_version(game_version)
        return None

    def latest_many(self, game_versions: Iterable[str]) -> dict[tuple[str, str], str]:
        found: dict[tuple[str, str], str] = {}
        for game_version in game_versions:
            for loader in LOADERS:
                try:
                    version = self.latest(loader, game_version)
                except LoaderMetaError:
                    logger.warning("No %s builds for %s", loader, game_version, exc_info=True)
                    continue
                if version:
                    found[(str(loader), game_version)] = version
        return found
