"""Loader meta answers (fixtures: loaders/)."""

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
