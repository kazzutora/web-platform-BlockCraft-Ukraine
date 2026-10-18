"""Pydantic models for the Mojang API answers we read."""

from pydantic import BaseModel, Field


class MojangProfileId(BaseModel):
    id: str
    name: str


class MojangProperty(BaseModel):
    name: str
    value: str


class MojangProfile(BaseModel):
    id: str
    name: str
    properties: list[MojangProperty] = Field(default_factory=list)


class TextureMetadata(BaseModel):
    model: str = "classic"


class Texture(BaseModel):
    url: str
    metadata: TextureMetadata = Field(default_factory=TextureMetadata)


class Textures(BaseModel):
    SKIN: Texture | None = None


class TexturesPayload(BaseModel):
    """The base64 JSON inside the `textures` property."""

    profileName: str
    textures: Textures = Field(default_factory=Textures)
