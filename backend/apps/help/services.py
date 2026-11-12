"""R8.5 «Вирішити проблему»: a pack for a goal, made from real catalog projects."""

from dataclasses import dataclass

from django.db import transaction

from apps.accounts.models import User
from apps.compat import services as compat
from apps.compat.types import Item, ItemStatus, Resolution, Target
from apps.core.exceptions import DomainError
from apps.mods.models import Project, ProjectType
from apps.packs import services as packs
from apps.packs.choices import MAX_ITEMS, PackLoader
from apps.packs.models import Pack, PackItem, Visibility
from apps.sources.services import NoGameVersionsError, supported_game_versions

from .goals import GOAL_TITLES, GOALS, Slot


@dataclass(frozen=True)
class Choice:
    slot: str
    slug: str | None


@dataclass(frozen=True)
class Preview:
    target: Target
    choices: list[Choice]
    resolved: compat.Resolved

    @property
    def picked(self) -> list[str]:
        return [choice.slug for choice in self.choices if choice.slug]


def check_target(target: Target) -> None:
    """A goal pack needs a mod loader: every goal is made of mods."""
    try:
        supported = set(supported_game_versions())
    except NoGameVersionsError:
        supported = set()  # an empty catalog: no version is known yet
    if target.loader not in PackLoader.values:
        raise DomainError(
            code="needs_mod_loader",
            message="Збірці потрібен лоадер модів: обери Fabric, Forge, NeoForge чи Quilt.",
            fields={"loader": ["Обери лоадер модів."]},
        )
    if target.game_version not in supported:
        raise DomainError(
            code="unknown_game_version",
            message="Обери версію гри зі списку.",
            fields={"game_version": ["Обери версію гри зі списку."]},
        )


def slots_for(goals: list[str]) -> list[Slot]:
    """The slots of the chosen goals in order; a slot shared by two goals comes once."""
    seen: dict[str, Slot] = {}
    for goal in goals:
        for slot in GOALS[goal]:
            seen.setdefault(slot.name, slot)
    return list(seen.values())


def _fits(project: Project, target: Target) -> bool:
    """Same rule as the catalog filter: project-level game versions and loaders."""
    if target.game_version not in project.game_versions:
        return False
    if project.project_type == ProjectType.MOD:
        return target.loader in project.loaders
    return True


def _pick(slots: list[Slot], rows: dict[str, Project], target: Target, banned: set[str]):
    picks: dict[str, str | None] = {}
    for slot in slots:
        if any(slug in picks.values() for slug in slot.unless):
            picks[slot.name] = None
            continue
        picks[slot.name] = next(
            (
                slug
                for slug in slot.candidates
                if slug not in banned and slug in rows and _fits(rows[slug], target)
            ),
            None,
        )
    return picks


def _roots(slug: str, items: dict[str, Item], chosen: list[str]) -> set[str]:
    """The picks that brought a project in: itself, or whoever requires it, transitively."""
    found: set[str] = set()
    stack, seen = [slug], set()
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        if current in chosen:
            found.add(current)
            continue
        item = items.get(current)
        if item is not None:
            stack.extend(item.required_by)
    return found


def _bad_picks(resolution: Resolution, chosen: list[str]) -> set[str]:
    """Picks that cannot stay: a file missing for the game (theirs or a dependency's), or a
    conflict, also with a dependency or an implicit engine (Iris) another pick brought."""
    items = {item.project.slug: item for item in resolution.items}
    bad: set[str] = set()
    for item in resolution.items:
        if item.status != ItemStatus.OK:
            bad |= _roots(item.project.slug, items, chosen)
    for conflict in resolution.conflicts:
        roots = _roots(conflict.a, items, chosen) | _roots(conflict.b, items, chosen)
        if roots:
            # The later pick (a less important slot) gives way
            bad.add(max(roots, key=chosen.index))
    return bad


def preview(*, goals: list[str], target: Target) -> Preview:
    """The best candidate of every slot that fits «Моя гра» and installs with the others.

    A pick that cannot stay (see `_bad_picks`) gives way to the next candidate of its slot;
    the engine adds what the picks depend on. Every round bans at least one more candidate,
    so the loop ends — at worst with fewer slots filled, never with a broken set.
    """
    check_target(target)
    slots = slots_for(goals)
    wanted = {slug for slot in slots for slug in slot.candidates}
    rows = {row.slug: row for row in Project.objects.visible().filter(slug__in=wanted)}
    banned: set[str] = set()
    for _ in range(len(wanted) + 1):
        picks = _pick(slots, rows, target, banned)
        chosen = [slug for slug in picks.values() if slug]
        resolved = compat.resolve(items=[(rows[slug], None) for slug in chosen], target=target)
        bad = _bad_picks(resolved.resolution, chosen)
        if not bad:
            break
        banned |= bad
    choices = [Choice(slot, slug) for slot, slug in picks.items()]
    return Preview(target=target, choices=choices, resolved=resolved)


def save_pack(*, user: User, goals: list[str], target: Target) -> Pack:
    """The preview as the player's private draft: they adjust it in the constructor."""
    found = preview(goals=goals, target=target)
    if not found.picked:
        raise DomainError(
            code="nothing_fits",
            message="Під цю версію гри й лоадер нічого з цілей не знайшлося.",
        )
    title = "Збірка: " + ", ".join(GOAL_TITLES[goal] for goal in dict.fromkeys(goals))
    rows = {row.slug: row for row in Project.objects.filter(slug__in=found.picked)}
    with transaction.atomic():
        pack = packs.create_pack(
            author=user,
            data={
                "title": title[:80],
                "game_version": target.game_version,
                "loader": target.loader,
                "visibility": Visibility.PRIVATE,
            },
        )
        PackItem.objects.bulk_create(
            PackItem(pack=pack, project=rows[slug], position=position)
            for position, slug in enumerate(found.picked[:MAX_ITEMS], start=1)
        )
        packs.rebuild(pack)
    packs.queue_cover(pack)
    return pack
