"""Modrinth API v2 responses: only the fields BlockCraft uses."""

from datetime import datetime

from pydantic import BaseModel, Field


class SearchHit(BaseModel):
    project_id: str
    slug: str
    project_type: str
    title: str


class SearchResponse(BaseModel):
    hits: list[SearchHit]
    offset: int
    limit: int
    total_hits: int


class GalleryImage(BaseModel):
    url: str
    raw_url: str | None = None
    featured: bool = False
    title: str | None = None
    description: str | None = None
    ordering: int = 0


class License(BaseModel):
    id: str = ""
    name: str = ""
    url: str | None = None


class ModrinthProject(BaseModel):
    id: str
    slug: str
    project_type: str
    title: str
    description: str = ""
    body: str = ""
    categories: list[str] = Field(default_factory=list)
    additional_categories: list[str] = Field(default_factory=list)
    loaders: list[str] = Field(default_factory=list)
    game_versions: list[str] = Field(default_factory=list)
    downloads: int = 0
    icon_url: str | None = None
    gallery: list[GalleryImage] = Field(default_factory=list)
    license: License | None = None
    source_url: str | None = None
    published: datetime
    updated: datetime


class VersionFile(BaseModel):
    url: str
    filename: str
    primary: bool = False
    size: int = 0
    hashes: dict[str, str] = Field(default_factory=dict)


class Dependency(BaseModel):
    version_id: str | None = None
    project_id: str | None = None
    file_name: str | None = None
    dependency_type: str


class ModrinthVersion(BaseModel):
    id: str
    project_id: str
    name: str = ""
    version_number: str
    version_type: str = "release"
    game_versions: list[str] = Field(default_factory=list)
    loaders: list[str] = Field(default_factory=list)
    date_published: datetime
    files: list[VersionFile] = Field(default_factory=list)
    dependencies: list[Dependency] = Field(default_factory=list)

    @property
    def primary_file(self) -> VersionFile | None:
        return next((file for file in self.files if file.primary), None) or next(
            iter(self.files), None
        )


class ModrinthCategory(BaseModel):
    name: str
    project_type: str
    header: str = ""
