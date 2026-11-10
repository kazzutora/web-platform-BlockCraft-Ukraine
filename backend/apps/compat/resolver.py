"""Picking versions and resolving dependencies (tech.md 9.2–9.4). Pure: no HTTP, no writes.

Projects come from an `Index`; whatever it does not know is returned in `missing`, and the
caller (a service) queues the import.
"""

from collections.abc import Iterable

from apps.core.versions import is_release, version_key

from . import rules
from .types import (
    Conflict,
    Index,
    Item,
    ItemStatus,
    Pick,
    Project,
    Reason,
    Request,
    Resolution,
    Suggestion,
    Target,
    Version,
    Warning,
)

#: Biggest set a single resolution takes (tech.md 9.3, `400 pack_too_large`)
MAX_PROJECTS = 300
_STABILITY = {"release": 0, "beta": 1, "alpha": 2}


class TooManyProjects(ValueError):
    pass


def candidates(project: Project, target: Target) -> list[Version]:
    """Versions for the target game version with a loader the target accepts, best first."""
    accepted = rules.accepted_loaders(target, project.project_type)
    found = [
        version
        for version in project.versions
        if target.game_version in version.game_versions and accepted.intersection(version.loaders)
    ]
    return sorted(
        found,
        key=lambda version: (
            _STABILITY.get(version.version_type, 3),
            -version.date_published.timestamp(),
        ),
    )


def nearest_game_versions(project: Project, target: Target, limit: int = 3) -> tuple[str, ...]:
    """Releases closest to the target that do have a file with an accepted loader."""
    accepted = rules.accepted_loaders(target, project.project_type)
    available = {
        game_version
        for version in project.versions
        if accepted.intersection(version.loaders)
        for game_version in version.game_versions
        if is_release(game_version)
    }
    return nearest_in_order(target.game_version, available, limit)


def nearest_in_order(target: str, available: set[str], limit: int = 3) -> tuple[str, ...]:
    """Neighbours of `target` in release order (tech.md 9.2), newer first on a tie.

    For 26.1 with files for 1.20.1 / 1.21 / 1.21.1 that is 1.21.1, 1.21, 1.20.1 — the
    releases a player would downgrade to, nearest first.
    """
    ordered = sorted(available | {target}, key=version_key)
    position = ordered.index(target)
    others = [version for version in ordered if version != target]
    others.sort(
        key=lambda version: (
            abs(ordered.index(version) - position),
            -ordered.index(version),
        )
    )
    return tuple(others[:limit])


def pick_version(project: Project, target: Target, pinned: str | None = None) -> Pick:
    """The file to install: the pinned one if it fits, else the newest most stable one."""
    found = candidates(project, target)
    if pinned:
        version = next((item for item in found if item.id == pinned), None)
        if version is not None:
            return Pick(version, ItemStatus.OK)
        return Pick(None, ItemStatus.PINNED_INCOMPATIBLE, nearest_game_versions(project, target))
    if found:
        return Pick(found[0], ItemStatus.OK)
    if rules.needs_loader(target, project.project_type):
        return Pick(None, ItemStatus.MOD_NEEDS_LOADER)
    return Pick(None, ItemStatus.NO_VERSION, nearest_game_versions(project, target))


def _entry(
    project: Project,
    reason: Reason,
    required_by: str | None = None,
    pinned: str | None = None,
) -> tuple[Project, Reason, str | None, str | None]:
    return project, reason, required_by, pinned


def resolve(requests: Iterable[Request], target: Target, index: Index) -> Resolution:
    """What to install for a set of projects: BFS over required dependencies.

    One project gets one version. Dependencies the index does not know go to `missing`;
    optional ones become suggestions; `incompatible` ones become conflicts when both ends
    are in the result. Projects of each BFS level are loaded from the index in one call.
    """
    requests = list(requests)
    if len(requests) > MAX_PROJECTS:
        raise TooManyProjects(f"At most {MAX_PROJECTS} projects at once")
    result = Resolution(target=target)
    chosen: dict[str, Item] = {}  # by project id
    forbids: list[tuple[str, str]] = []  # (project id, forbidden project id)
    suggested: dict[str, str] = {}  # optional project id → slug of who suggests it
    requested_ids = {request.project.id for request in requests}
    level = [
        _entry(request.project, Reason.REQUESTED, pinned=request.pinned_version_id)
        for request in requests
    ]

    while level:
        wanted: dict[str, list[tuple[str, str | None]]] = {}  # dep id → [(required_by, pin)]
        by_version: dict[str, list[str]] = {}  # version id of a dependency → [required_by]
        engines: dict[str, list[str]] = {}  # implicit mod slug → [required_by]
        for project, reason, required_by, pinned in level:
            existing = chosen.get(project.id)
            if existing is not None:
                if required_by and required_by not in existing.required_by:
                    existing.required_by.append(required_by)
                if pinned and existing.version is not None and existing.version.id != pinned:
                    result.warnings.append(
                        Warning(
                            "version_mismatch",
                            {"project": project.slug, "required_by": required_by or ""},
                        )
                    )
                continue
            pick = pick_version(project, target, pinned)
            if pinned and reason == Reason.DEPENDENCY and pick.status != ItemStatus.OK:
                # The author pinned a file that does not fit: take the best one we have
                pick = pick_version(project, target)
                if pick.version is not None:
                    result.warnings.append(
                        Warning(
                            "version_mismatch",
                            {"project": project.slug, "required_by": required_by or ""},
                        )
                    )
            item = Item(
                project=project,
                version=pick.version,
                reason=reason,
                status=pick.status,
                required_by=[required_by] if required_by else [],
                nearest_game_versions=pick.nearest_game_versions,
            )
            chosen[project.id] = item
            result.items.append(item)
            if pick.version is None:
                continue
            if pick.version.version_type != "release":
                result.warnings.append(Warning("beta_only", {"project": project.slug}))
            for dependency in pick.version.dependencies:
                if dependency.dependency_type == "embedded":
                    continue
                if not dependency.project_id:
                    # Only the file is named: find its project, pinned to that file
                    if dependency.version_id and dependency.dependency_type == "required":
                        by_version.setdefault(dependency.version_id, []).append(project.slug)
                    continue
                if dependency.dependency_type == "optional":
                    suggested.setdefault(dependency.project_id, project.slug)
                elif dependency.dependency_type == "incompatible":
                    forbids.append((project.id, dependency.project_id))
                elif dependency.dependency_type == "required":
                    wanted.setdefault(dependency.project_id, []).append(
                        (project.slug, dependency.version_id)
                    )
            if project.project_type == "shader":
                engine = rules.shader_engine(pick.version, target)
                if engine.mod:
                    engines.setdefault(engine.mod, []).append(project.slug)
                if engine.warning:
                    result.warnings.append(Warning(engine.warning, {"project": project.slug}))

        level = []
        known = index.projects(wanted) if wanted else {}
        for project_id, needers in wanted.items():
            dependency = known.get(project_id)
            if dependency is None:
                if project_id not in result.missing:
                    result.missing.append(project_id)
                continue
            for required_by, pin in needers:
                level.append(_entry(dependency, Reason.DEPENDENCY, required_by, pin))
        owners = index.by_version(by_version) if by_version else {}
        for version_id, needers in by_version.items():
            owner = owners.get(version_id)
            if owner is None:
                for required_by in needers:
                    result.warnings.append(
                        Warning("unknown_dependency", {"required_by": required_by})
                    )
                continue
            for required_by in needers:
                level.append(_entry(owner, Reason.DEPENDENCY, required_by, version_id))
        implicit = index.by_slug(engines) if engines else {}
        for slug, needers in engines.items():
            engine_project = implicit.get(slug)
            if engine_project is None:
                if slug not in result.missing:
                    result.missing.append(slug)
                continue
            for required_by in needers:
                level.append(_entry(engine_project, Reason.IMPLICIT, required_by))

    slugs = {project_id: item.project.slug for project_id, item in chosen.items()}
    pairs: set[frozenset[str]] = set()
    for project_id, other in forbids:
        # Only files that will be installed can clash; one pair is one conflict
        if other not in chosen or other == project_id or chosen[other].version is None:
            continue
        pair = frozenset({project_id, other})
        if pair in pairs:
            continue
        pairs.add(pair)
        result.conflicts.append(
            Conflict(a=slugs[project_id], b=slugs[other], declared_by=slugs[project_id])
        )
    result.suggestions = [
        Suggestion(project=project_id, suggested_by=slug)
        for project_id, slug in suggested.items()
        if project_id not in chosen and project_id not in requested_ids
    ]
    return result
