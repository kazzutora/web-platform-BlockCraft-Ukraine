"""MineSkin API v2 answers: only the fields BlockCraft reads (fixtures: mineskin/)."""

from typing import Literal

from pydantic import BaseModel, Field


class SkinSummary(BaseModel):
    """A row of the public gallery: no model and no texture URL, only the texture hash."""

    uuid: str
    name: str | None = None
    texture: str
    timestamp: int


class Cursor(BaseModel):
    after: str | None = None


class Pagination(BaseModel):
    next: Cursor = Field(default_factory=Cursor)


class SkinPage(BaseModel):
    skins: list[SkinSummary]
    pagination: Pagination = Field(default_factory=Pagination)

    @property
    def next_after(self) -> str | None:
        return self.pagination.next.after


class TextureHash(BaseModel):
    skin: str


class TextureUrl(BaseModel):
    skin: str


class Texture(BaseModel):
    hash: TextureHash
    url: TextureUrl


class Skin(BaseModel):
    uuid: str
    name: str | None = None
    visibility: str = "public"
    variant: Literal["classic", "slim"] | None = None
    texture: Texture
    tags: list[str | dict] = Field(default_factory=list)
    views: int = 0
    duplicate: bool = False


class SkinResponse(BaseModel):
    skin: Skin
