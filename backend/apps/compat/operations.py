"""Operations built on `resolve` (tech.md 9.5). Pure, like the resolver."""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field

from apps.core.versions import is_release, version_key

from . import rules
from .types import Resolution, Target, Version


@dataclass(frozen=True)
class Current:
    """What a pack holds now: a project and its file (None when nothing fits)."""

    slug: str
    version_id: str | None


@dataclass
class Retarget:
    """Moving a pack to another game: what stays, what changes, what falls out, what joins."""

    kept: list[str] = field(default_factory=list)
    #: (slug, old version id or None, new version id)
    changed: list[tuple[str, str | None, str]] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)


def retarget(current: Iterable[Current], after: Resolution) -> Retarget:
    """Compares a pack's items with its resolution for a new target."""
    before = {item.slug: item.version_id for item in current}
    result = Retarget()
    for item in after.items:
        slug = item.project.slug
        new = item.version.id if item.version else None
        if slug not in before:
            if new is not None:
                result.added.append(slug)
            continue
        if new is None:
            result.dropped.append(slug)
        elif before[slug] == new:
            result.kept.append(slug)
        else:
            result.changed.append((slug, before[slug], new))
    # Dependencies the new set no longer needs disappear quietly: they were never chosen
    return result


@dataclass(frozen=True)
class Guess:
    target: Target | None
    #: How many identified files fit the guess, out of how many were identified
    fitting: int = 0
    identified: int = 0


def guess_target(versions: Iterable[Version]) -> Guess:
    """«Схоже, це 1.21.1 · Fabric»: the game version and loader most identified files share.

    Each file votes for every release it supports and every mod loader it is built for;
    the winner is the newest release with the most votes, then the loader with the most
    votes among files supporting it.
    """
    files = [version for version in versions if set(version.loaders) & rules.MOD_LOADERS]
    if not files:
        return Guess(None)
    game_votes = Counter(
        game for version in files for game in set(version.game_versions) if is_release(game)
    )
    if not game_votes:
        return Guess(None, identified=len(files))
    game = max(game_votes, key=lambda name: (game_votes[name], version_key(name)))
    fitting = [version for version in files if game in version.game_versions]
    loader_votes = Counter(
        loader for version in fitting for loader in set(version.loaders) & rules.MOD_LOADERS
    )
    loader = max(sorted(loader_votes), key=lambda name: loader_votes[name])
    accepted = rules.accepted_loaders(Target(game, loader), "mod")
    fits = sum(1 for version in fitting if accepted & set(version.loaders))
    return Guess(Target(game, loader), fitting=fits, identified=len(files))
