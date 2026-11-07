"""Modrinth API v3 server projects: only the fields BlockCraft reads (fixtures: modrinth_v3/).

v3 is undocumented: these models follow the recorded answers, and an unknown `content.kind`
fails validation on purpose (docs/sources.md).
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class ServerSearchHit(BaseModel):
    project_id: str
    slug: str
    name: str


class ServerSearchResponse(BaseModel):
    hits: list[ServerSearchHit]
    page: int
    hits_per_page: int
    total_hits: int


class VanillaContent(BaseModel):
    kind: Literal["vanilla"]
    supported_game_versions: list[str] = Field(default_factory=list)
    recommended_game_version: str | None = None


class ModpackContent(BaseModel):
    """`project_id` equal to the server's own id: the pack is uploaded into the server project."""

    kind: Literal["modpack"]
    project_id: str
    version_id: str
    project_name: str = ""


Content = Annotated[VanillaContent | ModpackContent, Field(discriminator="kind")]


class PingData(BaseModel):
    version_name: str = ""
    players_online: int = 0
    players_max: int = 0


class Ping(BaseModel):
    when: datetime
    data: PingData | None = None


class JavaServer(BaseModel):
    address: str
    content: Content
    ping: Ping | None = None
    verified_plays_2w: int = 0
    verified_plays_4w: int = 0


class MinecraftServer(BaseModel):
    max_players: int | None = None
    #: ISO 3166-1 alpha-2, often missing
    country: str | None = None
    region: str | None = None
    #: ISO 639-1 codes
    languages: list[str] = Field(default_factory=list)


class Link(BaseModel):
    url: str


class GalleryImage(BaseModel):
    url: str
    featured: bool = False
    name: str | None = None
    ordering: int = 0


class ServerProject(BaseModel):
    id: str
    slug: str
    name: str
    summary: str = ""
    description: str = ""
    categories: list[str] = Field(default_factory=list)
    icon_url: str | None = None
    gallery: list[GalleryImage] = Field(default_factory=list)
    link_urls: dict[str, Link] = Field(default_factory=dict)
    published: datetime
    updated: datetime
    minecraft_server: MinecraftServer
    minecraft_java_server: JavaServer

    @property
    def has_own_pack(self) -> bool:
        content = self.minecraft_java_server.content
        return isinstance(content, ModpackContent) and content.project_id == self.id
