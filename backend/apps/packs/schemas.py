"""External formats: loader meta APIs and Modrinth's modrinth.index.json (formatVersion 1)."""

from pydantic import BaseModel, Field


class LoaderBuild(BaseModel):
    version: str
    #: Fabric marks stable builds; Quilt marks pre-releases with a "-beta.N" suffix instead
    stable: bool | None = None


class LoaderEntry(BaseModel):
    """One row of meta.fabricmc.net / meta.quiltmc.org `versions/loader/{game}`."""

    loader: LoaderBuild


class ForgePromotions(BaseModel):
    promos: dict[str, str] = Field(default_factory=dict)


class MavenVersions(BaseModel):
    versions: list[str] = Field(default_factory=list)


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
