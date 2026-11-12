"""Mods named in a crash log → catalog projects (the log itself stays in the browser)."""

from django.db.models import Q

from apps.core.kinds import Viewer
from apps.mods import selectors as mods
from apps.mods.models import Project, ProjectType
from apps.packs.models import LoaderRelease

#: Mod ids that are the game, the loader or Java: nothing to look up in the catalog
NOT_PROJECTS = frozenset(
    {
        "minecraft",
        "java",
        "fabricloader",
        "fabric-loader",
        "forge",
        "neoforge",
        "fml",
        "quilt_loader",
    }
)
#: Mod ids that differ from the Modrinth slug and the title does not help either
ALIASES = {
    # Fabric API's mod id was «fabric» before it became «fabric-api»
    "fabric": "fabric-api",
}


def _slugs(mod_id: str) -> list[str]:
    lowered = mod_id.lower()
    return list(dict.fromkeys([ALIASES.get(lowered, lowered), lowered.replace("_", "-")]))


def match_mods(*, mods_found: list[dict], viewer: Viewer) -> dict[str, Project | None]:
    """`{id: project or None}` for every mod id of the log, in one query.

    A Modrinth slug usually is the mod id (or the id with dashes); otherwise the display
    name from the log matches the title. What is left is «not in our catalog».
    """
    wanted = [mod for mod in mods_found if mod["id"].lower() not in NOT_PROJECTS]
    if not wanted:
        return {}
    slugs = {slug for mod in wanted for slug in _slugs(mod["id"])}
    titles = {mod["name"].lower() for mod in wanted if mod.get("name")}
    query = Q(slug__in=slugs)
    named = Q()
    for title in titles:
        named |= Q(title__iexact=title)
    if titles:
        # Only mods have a mod id in a log: a shader or a resource pack of the same name is not it
        query |= Q(project_type=ProjectType.MOD) & named
    # Ascending: the most downloaded of two mods with one title is written last and wins
    rows = list(mods.catalog(viewer).filter(query).order_by("modrinth_downloads"))
    by_slug = {row.slug: row for row in rows}
    by_title = {row.title.lower(): row for row in rows if row.project_type == ProjectType.MOD}
    found: dict[str, Project | None] = {}
    for mod in wanted:
        row = next((by_slug[slug] for slug in _slugs(mod["id"]) if slug in by_slug), None)
        if row is None and mod.get("name"):
            row = by_title.get(mod["name"].lower())
        found[mod["id"]] = row
    return found


def loader_release(*, loader: str, game_version: str) -> LoaderRelease | None:
    """The latest stable loader for the game, for «онови лоадер»."""
    if not (loader and game_version):
        return None
    return LoaderRelease.objects.filter(loader=loader, game_version=game_version).first()
