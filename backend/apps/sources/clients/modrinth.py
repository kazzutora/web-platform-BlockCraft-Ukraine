"""Modrinth API v2 client (docs/sources.md). Call it only from Celery tasks and commands."""

import io
import json
import zipfile
from collections.abc import Callable, Iterable
from urllib.parse import urlsplit

import httpx
from pydantic import TypeAdapter

from ..schemas.modrinth import (
    ModrinthCategory,
    ModrinthGameVersion,
    ModrinthProject,
    ModrinthVersion,
    SearchResponse,
)
from .base import BaseClient, SourceError, SourceNotFoundError

BASE_URL = "https://api.modrinth.com/v2"
CDN_HOST = "cdn.modrinth.com"
# zipfile reads in small steps; one range request per 256 KB keeps it to a few calls
RANGE_CHUNK = 256 * 1024

_projects = TypeAdapter(list[ModrinthProject])
_versions = TypeAdapter(list[ModrinthVersion])
_categories = TypeAdapter(list[ModrinthCategory])
_game_versions = TypeAdapter(list[ModrinthGameVersion])


class ModrinthError(SourceError):
    """Modrinth did not answer after all retries, or answered with an unexpected error."""


class ModrinthNotFoundError(ModrinthError, SourceNotFoundError):
    pass


class ModrinthClient(BaseClient):
    name = "Modrinth"
    base_url = BASE_URL
    error = ModrinthError
    not_found_error = ModrinthNotFoundError

    # API

    def search(
        self,
        *,
        project_type: str,
        game_versions: Iterable[str] = (),
        offset: int = 0,
        limit: int = 100,
    ) -> SearchResponse:
        facets = [[f"project_type:{project_type}"]]
        versions = [f"versions:{version}" for version in game_versions]
        if versions:
            facets.append(versions)
        data = self.get_json(
            "/search",
            {"facets": json.dumps(facets), "index": "downloads", "offset": offset, "limit": limit},
        )
        return self.parse(SearchResponse, data)

    def get_projects(self, ids: list[str]) -> list[ModrinthProject]:
        if not ids:
            return []
        return self.parse(_projects, self.get_json("/projects", {"ids": json.dumps(ids)}))

    def get_project(self, id_or_slug: str) -> ModrinthProject:
        return self.parse(ModrinthProject, self.get_json(f"/project/{id_or_slug}"))

    def get_versions(
        self, project_id: str, *, game_versions: Iterable[str] = (), loaders: Iterable[str] = ()
    ) -> list[ModrinthVersion]:
        params: dict[str, str] = {}
        if game_versions:
            params["game_versions"] = json.dumps(list(game_versions))
        if loaders:
            params["loaders"] = json.dumps(list(loaders))
        return self.parse(_versions, self.get_json(f"/project/{project_id}/version", params))

    def get_categories(self) -> list[ModrinthCategory]:
        return self.parse(_categories, self.get_json("/tag/category"))

    def get_game_versions(self) -> list[ModrinthGameVersion]:
        """Every Minecraft version Modrinth knows, newest first (`/tag/game_version`)."""
        return self.parse(_game_versions, self.get_json("/tag/game_version"))

    def _range(self, url: str, start: int, end: int) -> bytes:
        try:
            response = self._client.get(url, headers={"Range": f"bytes={start}-{end}"})
        except httpx.TransportError as error:
            raise ModrinthError(f"GET {url}: {error}") from error
        if response.status_code == 404:
            raise ModrinthNotFoundError(f"GET {url}: not found")
        if response.status_code != 206:
            # A 200 would be the whole file: modpacks with configs weigh hundreds of MB
            raise ModrinthError(f"GET {url}: HTTP {response.status_code} to a range request")
        return response.content

    def read_zip_member(self, url: str, *, size: int, name: str, max_bytes: int) -> bytes:
        """One file of a zip on Modrinth's CDN, read with HTTP ranges, never the whole archive.

        Raises zipfile.BadZipFile or KeyError when the archive is broken or lacks `name`.
        """
        if urlsplit(url).hostname != CDN_HOST:
            raise ModrinthError(f"{url}: not a Modrinth CDN file")
        remote = io.BufferedReader(
            _RangeReader(lambda start, end: self._range(url, start, end), size),
            buffer_size=RANGE_CHUNK,
        )
        with zipfile.ZipFile(remote) as archive:
            if archive.getinfo(name).file_size > max_bytes:
                raise ModrinthError(f"{url}: {name} is larger than {max_bytes} bytes")
            return archive.read(name)


class _RangeReader(io.RawIOBase):
    """A seekable read-only remote file; zipfile only reads the directory and one member."""

    def __init__(self, fetch: Callable[[int, int], bytes], size: int) -> None:
        self._fetch = fetch
        self._size = size
        self._position = 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._position

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self._position, io.SEEK_END: self._size}[whence]
        self._position = max(0, base + offset)
        return self._position

    def readinto(self, buffer) -> int:
        end = min(self._position + len(buffer), self._size)
        if end <= self._position:
            return 0
        data = self._fetch(self._position, end - 1)
        buffer[: len(data)] = data
        self._position += len(data)
        return len(data)
