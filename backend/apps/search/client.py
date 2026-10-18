"""Meilisearch REST API over httpx: the handful of calls the search app needs."""

import time
from collections.abc import Callable
from typing import Any, Self

import httpx
from django.conf import settings


class SearchUnavailableError(Exception):
    """Meilisearch did not answer or answered with an error."""


class MeiliClient:
    def __init__(
        self,
        *,
        url: str | None = None,
        key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 5.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        key = settings.MEILI_MASTER_KEY if key is None else key
        self._client = httpx.Client(
            base_url=url or settings.MEILI_URL,
            timeout=timeout,
            headers={"Authorization": f"Bearer {key}"} if key else {},
            transport=transport,
        )
        self._sleep = sleep

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._client.close()

    def _request(self, method: str, path: str, **kwargs) -> Any:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.HTTPError as error:
            raise SearchUnavailableError(f"{method} {path}: {error}") from error
        if response.status_code >= 400:
            raise SearchUnavailableError(
                f"{method} {path}: HTTP {response.status_code} {response.text[:200]}"
            )
        return response.json() if response.content else None

    def wait(self, task: dict, *, timeout: float = 60.0) -> dict:
        """Index changes are asynchronous in Meilisearch: wait for the task to finish."""
        deadline = time.monotonic() + timeout
        while True:
            state = self._request("GET", f"/tasks/{task['taskUid']}")
            if state["status"] == "succeeded":
                return state
            if state["status"] in ("failed", "canceled"):
                raise SearchUnavailableError(f"task {task['taskUid']}: {state.get('error')}")
            if time.monotonic() > deadline:
                raise SearchUnavailableError(f"task {task['taskUid']} is still {state['status']}")
            self._sleep(0.2)

    def create_index(self, uid: str, *, primary_key: str) -> dict:
        return self._request("POST", "/indexes", json={"uid": uid, "primaryKey": primary_key})

    def delete_index(self, uid: str) -> dict:
        return self._request("DELETE", f"/indexes/{uid}")

    def index_exists(self, uid: str) -> bool:
        try:
            self._request("GET", f"/indexes/{uid}")
        except SearchUnavailableError:
            return False
        return True

    def update_settings(self, uid: str, index_settings: dict) -> dict:
        return self._request("PATCH", f"/indexes/{uid}/settings", json=index_settings)

    def add_documents(self, uid: str, documents: list[dict]) -> dict:
        return self._request("POST", f"/indexes/{uid}/documents", json=documents)

    def delete_documents(self, uid: str, ids: list[str]) -> dict:
        return self._request("POST", f"/indexes/{uid}/documents/delete-batch", json=ids)

    def swap_indexes(self, first: str, second: str) -> dict:
        return self._request("POST", "/swap-indexes", json=[{"indexes": [first, second]}])

    def multi_search(self, queries: list[dict]) -> list[dict]:
        return self._request("POST", "/multi-search", json={"queries": queries})["results"]
