"""MineSkin API v2: the public skin gallery (docs/sources.md, «MineSkin»). Celery only."""

from django.conf import settings

from ..schemas.mineskin import Skin, SkinPage, SkinResponse
from .base import BaseClient, SourceError, SourceNotFoundError

BASE_URL = "https://api.mineskin.org"
#: Page size is not documented; small pages keep one failure cheap
PAGE_SIZE = 32


class MineSkinError(SourceError):
    pass


class MineSkinNotFoundError(MineSkinError, SourceNotFoundError):
    pass


class MineSkinClient(BaseClient):
    name = "MineSkin"
    base_url = BASE_URL
    error = MineSkinError
    not_found_error = MineSkinNotFoundError

    def headers(self) -> dict[str, str]:
        key = settings.MINESKIN_API_KEY
        return {"Authorization": f"Bearer {key}"} if key else {}

    def list_skins(self, *, after: str | None = None, size: int = PAGE_SIZE) -> SkinPage:
        """One page of the gallery, newest first; pass `next_after` for the next one."""
        params: dict[str, str | int] = {"size": size}
        if after:
            params["after"] = after
        return self.parse(SkinPage, self.get_json("/v2/skins", params))

    def get_skin(self, uuid: str) -> Skin:
        return self.parse(SkinResponse, self.get_json(f"/v2/skins/{uuid}")).skin
