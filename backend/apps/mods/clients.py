"""Modrinth API v2 client. Call it only from Celery tasks and management commands."""

import io
import json
import logging
import time
import zipfile
from collections.abc import Callable, Iterable
from typing import Any, Self
from urllib.parse import urlsplit

import httpx
from django.conf import settings
from pydantic import TypeAdapter

from .schemas import ModrinthCategory, ModrinthProject, ModrinthVersion, SearchResponse

logger = logging.getLogger(__name__)

BASE_URL = "https://api.modrinth.com/v2"
CDN_HOST = "cdn.modrinth.com"
# zipfile reads in small steps; one range request per 256 KB keeps it to a few calls
RANGE_CHUNK = 256 * 1024
MAX_RETRY_DELAY = 60.0

_projects = TypeAdapter(list[ModrinthProject])
_versions = TypeAdapter(list[ModrinthVersion])
_categories = TypeAdapter(list[ModrinthCategory])


class ModrinthError(Exception):
    """Modrinth did not answer after all retries, or answered with an unexpected error."""


class ModrinthNotFoundError(ModrinthError):
    pass


class ModrinthClient:
    def __init__(
        self,
        *,
        user_agent: str | None = None,
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 3,
        backoff: float = 0.5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = httpx.Client(
            base_url=BASE_URL,
            timeout=10.0,
            headers={"User-Agent": user_agent or settings.MODRINTH_USER_AGENT},
            transport=transport,
        )
        self._max_retries = max_retries
        self._backoff = backoff
        self._sleep = sleep

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    # Transport

    def _retry_delay(self, response: httpx.Response | None, attempt: int) -> float:
        if response is not None and response.status_code == 429:
            for header in ("Retry-After", "X-Ratelimit-Reset"):
                value = response.headers.get(header)
                if value and value.replace(".", "", 1).isdigit():
                    return min(float(value) or 1.0, MAX_RETRY_DELAY)
        return min(self._backoff * 2**attempt, MAX_RETRY_DELAY)

    def _respect_rate_limit(self, response: httpx.Response) -> None:
        """Waits for the window reset when the remaining budget is almost spent (300/min)."""
        remaining = response.headers.get("X-Ratelimit-Remaining")
        reset = response.headers.get("X-Ratelimit-Reset")
        if remaining is not None and reset and remaining.isdigit() and int(remaining) <= 2:
            delay = min(float(reset), MAX_RETRY_DELAY) if reset.isdigit() else 1.0
            logger.info("Modrinth rate limit almost reached, waiting %.1fs", delay)
            self._sleep(delay)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        for attempt in range(self._max_retries + 1):
            response: httpx.Response | None = None
            try:
                response = self._client.get(path, params=params)
            except httpx.TransportError as error:
                if attempt == self._max_retries:
                    raise ModrinthError(f"GET {path}: {error}") from error
            else:
                if response.status_code == 404:
                    raise ModrinthNotFoundError(f"GET {path}: not found")
                if response.status_code != 429 and response.status_code < 500:
                    response.raise_for_status()
                    self._respect_rate_limit(response)
                    return response.json()
                if attempt == self._max_retries:
                    raise ModrinthError(f"GET {path}: HTTP {response.status_code}")
            delay = self._retry_delay(response, attempt)
            logger.warning(
                "Modrinth GET %s failed (attempt %d), retrying in %.1fs", path, attempt + 1, delay
            )
            self._sleep(delay)
        raise ModrinthError(f"GET {path}: retries exhausted")  # pragma: no cover

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
        data = self._get(
            "/search",
            {"facets": json.dumps(facets), "index": "downloads", "offset": offset, "limit": limit},
        )
        return SearchResponse.model_validate(data)

    def get_projects(self, ids: list[str]) -> list[ModrinthProject]:
        if not ids:
            return []
        return _projects.validate_python(self._get("/projects", {"ids": json.dumps(ids)}))

    def get_project(self, id_or_slug: str) -> ModrinthProject:
        return ModrinthProject.model_validate(self._get(f"/project/{id_or_slug}"))

    def get_versions(
        self, project_id: str, *, game_versions: Iterable[str] = (), loaders: Iterable[str] = ()
    ) -> list[ModrinthVersion]:
        params: dict[str, str] = {}
        if game_versions:
            params["game_versions"] = json.dumps(list(game_versions))
        if loaders:
            params["loaders"] = json.dumps(list(loaders))
        return _versions.validate_python(self._get(f"/project/{project_id}/version", params))

    def get_categories(self) -> list[ModrinthCategory]:
        return _categories.validate_python(self._get("/tag/category"))

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
