"""Shared HTTP layer of every source client (docs/tech.md, 8).

httpx with a timeout, retries with backoff on 5xx and network errors, a pause on 429 by
`Retry-After` / `X-Ratelimit-Reset`, and pydantic validation that turns a changed answer
into `SourceSchemaError`. Call clients only from Celery tasks, management commands or
behind a cache.
"""

import logging
import time
from collections.abc import Callable
from typing import Any, Self, TypeVar, overload

import httpx
from django.conf import settings
from pydantic import BaseModel, TypeAdapter, ValidationError

logger = logging.getLogger(__name__)

MAX_RETRY_DELAY = 60.0
Model = TypeVar("Model", bound=BaseModel)
T = TypeVar("T")


class SourceError(Exception):
    """The source did not answer after all retries, or answered with an unexpected error."""


class SourceNotFoundError(SourceError):
    """The source does not know the requested object."""


class SourceRateLimitedError(SourceError):
    """The source asked us to slow down and the client does not wait for it."""


class SourceSchemaError(SourceError):
    """The answer no longer matches the recorded schema: the source changed its API."""


class BaseClient:
    name = "source"
    base_url = ""
    timeout = 10.0
    max_retries = 3
    backoff = 0.5
    follow_redirects = False
    not_found_statuses: frozenset[int] = frozenset({404})
    #: False: a 429 raises `rate_limited_error` at once (user-facing lookups must not wait)
    wait_on_429 = True

    error: type[SourceError] = SourceError
    not_found_error: type[SourceNotFoundError] = SourceNotFoundError
    rate_limited_error: type[SourceRateLimitedError] = SourceRateLimitedError

    def __init__(
        self,
        *,
        user_agent: str | None = None,
        transport: httpx.BaseTransport | None = None,
        max_retries: int | None = None,
        backoff: float | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"User-Agent": user_agent or settings.SOURCES_USER_AGENT, **self.headers()},
            transport=transport,
            follow_redirects=self.follow_redirects,
        )
        self._max_retries = self.max_retries if max_retries is None else max_retries
        self._backoff = self.backoff if backoff is None else backoff
        # Looked up at call time, so tests can patch time.sleep
        self._sleep = sleep or (lambda seconds: time.sleep(seconds))

    def headers(self) -> dict[str, str]:
        """Extra headers of the source, e.g. an API key."""
        return {}

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
        """Waits for the window reset when the remaining budget is almost spent."""
        remaining = response.headers.get("X-Ratelimit-Remaining")
        reset = response.headers.get("X-Ratelimit-Reset")
        if remaining is not None and reset and remaining.isdigit() and int(remaining) <= 2:
            delay = min(float(reset), MAX_RETRY_DELAY) if reset.isdigit() else 1.0
            logger.info("%s rate limit almost reached, waiting %.1fs", self.name, delay)
            self._sleep(delay)

    def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> httpx.Response:
        label = f"{self.name} {method} {url}"
        for attempt in range(self._max_retries + 1):
            response: httpx.Response | None = None
            try:
                response = self._client.request(method, url, params=params, json=json)
            except httpx.TransportError as error:
                if attempt == self._max_retries:
                    raise self.error(f"{label}: {error}") from error
            else:
                status = response.status_code
                if status in self.not_found_statuses:
                    raise self.not_found_error(f"{label}: not found")
                if status == 429 and not self.wait_on_429:
                    raise self.rate_limited_error(f"{label}: rate limited")
                if status != 429 and status < 500:
                    if status >= 400:
                        raise self.error(f"{label}: HTTP {status}")
                    self._respect_rate_limit(response)
                    return response
                if attempt == self._max_retries:
                    raise self.error(f"{label}: HTTP {status}")
            delay = self._retry_delay(response, attempt)
            logger.warning("%s failed (attempt %d), retrying in %.1fs", label, attempt + 1, delay)
            self._sleep(delay)
        raise self.error(f"{label}: retries exhausted")  # pragma: no cover

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        return self.json_of(self.request("GET", url, params=params))

    def post_json(self, url: str, body: Any) -> Any:
        return self.json_of(self.request("POST", url, json=body))

    def json_of(self, response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError as error:
            raise SourceSchemaError(f"{self.name} {response.request.url}: not JSON") from error

    # Validation

    @overload
    def parse(self, schema: type[Model], data: Any) -> Model: ...

    @overload
    def parse(self, schema: TypeAdapter[T], data: Any) -> T: ...

    def parse(self, schema, data):
        """Validates `data` against the recorded schema; a mismatch is `SourceSchemaError`."""
        try:
            if isinstance(schema, TypeAdapter):
                return schema.validate_python(data)
            return schema.model_validate(data)
        except ValidationError as error:
            raise SourceSchemaError(
                f"{self.name}: answer does not match the schema: {error}"
            ) from error
