"""Modrinth API v3: server projects (docs/sources.md, «Modrinth API v3»). Celery only.

v3 is not documented; a changed answer raises `SourceSchemaError`, so the sync fails and
the site keeps the data it has.
"""

import json

from ..schemas.modrinth_v3 import ServerProject, ServerSearchResponse
from .base import BaseClient
from .modrinth import ModrinthError, ModrinthNotFoundError

BASE_URL = "https://api.modrinth.com/v3"
SERVER_TYPE = "minecraft_java_server"


class ModrinthV3Client(BaseClient):
    name = "Modrinth v3"
    base_url = BASE_URL
    error = ModrinthError
    not_found_error = ModrinthNotFoundError

    def search_servers(
        self,
        *,
        language: str | None = None,
        content_kind: str | None = None,
        index: str = "relevance",
        offset: int = 0,
        limit: int = 20,
    ) -> ServerSearchResponse:
        """Java servers; `language` is ISO 639-1, `content_kind` is vanilla or modpack.

        Country has no working facet: filter it after loading the projects.
        """
        facets = [[f"project_types:{SERVER_TYPE}"]]
        if language:
            facets.append([f"minecraft_server.languages:{language}"])
        if content_kind:
            facets.append([f"minecraft_java_server.content.kind:{content_kind}"])
        data = self.get_json(
            "/search",
            {"facets": json.dumps(facets), "index": index, "offset": offset, "limit": limit},
        )
        return self.parse(ServerSearchResponse, data)

    def get_server(self, project_id: str) -> ServerProject:
        return self.parse(ServerProject, self.get_json(f"/project/{project_id}"))
