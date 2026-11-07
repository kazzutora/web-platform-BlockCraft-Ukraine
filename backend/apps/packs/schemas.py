"""Modrinth's modrinth.index.json (formatVersion 1), read from .mrpack files."""

from pydantic import BaseModel, Field


class MrpackEnv(BaseModel):
    client: str = "required"
    server: str = "required"


class MrpackFile(BaseModel):
    path: str
    hashes: dict[str, str]
    env: MrpackEnv | None = None
    downloads: list[str]
    fileSize: int = 0


class MrpackIndex(BaseModel):
    formatVersion: int
    game: str
    versionId: str = ""
    name: str = ""
    summary: str | None = None
    files: list[MrpackFile] = Field(default_factory=list)
    dependencies: dict[str, str] = Field(default_factory=dict)
