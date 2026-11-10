"""Data the compatibility engine works on and returns (tech.md 9). Plain values, no ORM."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol


@dataclass(frozen=True)
class Target:
    """«Моя гра»: the game version and loader everything is picked for."""

    game_version: str
    loader: str


@dataclass(frozen=True)
class Dependency:
    project_id: str | None
    version_id: str | None
    dependency_type: str  # required / optional / incompatible / embedded


@dataclass(frozen=True)
class Version:
    id: str
    project_id: str
    version_number: str
    version_type: str  # release / beta / alpha
    game_versions: tuple[str, ...]
    loaders: tuple[str, ...]
    date_published: datetime
    dependencies: tuple[Dependency, ...] = ()
    file_url: str = ""
    file_name: str = ""
    file_size: int = 0


@dataclass(frozen=True)
class Project:
    id: str  # Modrinth project id
    slug: str
    title: str
    project_type: str  # mod / resourcepack / shader / datapack
    icon_url: str = ""
    versions: tuple[Version, ...] = ()


class Index(Protocol):
    """Where projects come from; the engine asks once per BFS level (tech.md 9.3)."""

    def projects(self, ids: Iterable[str]) -> Mapping[str, Project]:
        """Known projects by Modrinth id; unknown ids are simply absent."""
        ...

    def by_slug(self, slugs: Iterable[str]) -> Mapping[str, Project]:
        """Known projects by slug (implicit dependencies are named by slug)."""
        ...

    def by_version(self, version_ids: Iterable[str]) -> Mapping[str, Project]:
        """Projects that own these version ids (a dependency may name only its version)."""
        ...


@dataclass(frozen=True)
class Request:
    project: Project
    pinned_version_id: str | None = None


class Reason(StrEnum):
    REQUESTED = "requested"
    DEPENDENCY = "dependency"
    IMPLICIT = "implicit"


class ItemStatus(StrEnum):
    OK = "ok"
    NO_VERSION = "no_version"
    PINNED_INCOMPATIBLE = "pinned_incompatible"
    #: A mod in a game without a loader (vanilla) and no datapack file to fall back on
    MOD_NEEDS_LOADER = "mod_needs_loader"


class Status(StrEnum):
    OK = "ok"
    WARNINGS = "warnings"
    ERRORS = "errors"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True)
class Pick:
    """`pick_version` answer: the version, or why there is none."""

    version: Version | None
    status: ItemStatus
    nearest_game_versions: tuple[str, ...] = ()


@dataclass
class Item:
    project: Project
    version: Version | None
    reason: Reason
    status: ItemStatus
    required_by: list[str] = field(default_factory=list)  # slugs
    nearest_game_versions: tuple[str, ...] = ()


@dataclass(frozen=True)
class Conflict:
    a: str  # slug
    b: str  # slug
    declared_by: str  # slug of the project whose version forbids the other


@dataclass(frozen=True)
class Suggestion:
    project: str  # Modrinth id: optional dependencies may be outside the catalog
    suggested_by: str  # slug


@dataclass(frozen=True)
class Warning:
    code: str  # version_mismatch, optifine_manual, beta_only, …
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Resolution:
    target: Target
    items: list[Item] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    suggestions: list[Suggestion] = field(default_factory=list)
    #: Modrinth ids (or slugs of implicit dependencies) we do not have yet
    missing: list[str] = field(default_factory=list)
    #: Required dependencies Modrinth does not have either (deleted, private): set by the
    #: caller from what its imports could not bring
    unavailable: list[str] = field(default_factory=list)
    warnings: list[Warning] = field(default_factory=list)

    @property
    def status(self) -> Status:
        if self.missing:
            return Status.INCOMPLETE
        if (
            self.unavailable
            or self.conflicts
            or any(item.status != ItemStatus.OK for item in self.items)
        ):
            return Status.ERRORS
        return Status.WARNINGS if self.warnings else Status.OK

    def item(self, slug: str) -> Item | None:
        return next((item for item in self.items if item.project.slug == slug), None)
