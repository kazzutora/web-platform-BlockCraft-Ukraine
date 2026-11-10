"""Knowledge about Minecraft the engine relies on (tech.md 9.1). Checked on real Modrinth data.

Each rule is a small pure function so tests can name the case they cover.
"""

from dataclasses import dataclass

from .types import Project, Target, Version

FABRIC, FORGE, NEOFORGE, QUILT, VANILLA = "fabric", "forge", "neoforge", "quilt", "vanilla"
MOD_LOADERS = frozenset({FABRIC, FORGE, NEOFORGE, QUILT})

#: NeoForge forked from Forge in 1.20.1: that release still loads Forge mods
NEOFORGE_LOADS_FORGE = frozenset({"1.20.1"})

#: Resource packs say `minecraft`; a few on Modrinth say `vanilla` (seen in R3.1)
RESOURCEPACK_LOADERS = frozenset({"minecraft", VANILLA})
DATAPACK_LOADERS = frozenset({"datapack"})
SHADER_LOADERS = frozenset({"iris", "optifine", "canvas", VANILLA})


def accepted_loaders(target: Target, project_type: str) -> frozenset[str]:
    """Version loaders that run in the target game. Empty means nothing of this type does."""
    if project_type == "resourcepack":
        return RESOURCEPACK_LOADERS
    if project_type == "datapack":
        return DATAPACK_LOADERS
    if project_type == "shader":
        if target.loader == VANILLA:
            # Core shaders work without mods; OptiFine is installed by hand
            return frozenset({VANILLA, "optifine"})
        if target.loader in {FABRIC, QUILT}:
            return SHADER_LOADERS
        # Canvas exists only for Fabric / Quilt
        return SHADER_LOADERS - {"canvas"}
    # Mods
    if target.loader == FABRIC:
        return frozenset({FABRIC})
    if target.loader == QUILT:
        return frozenset({QUILT, FABRIC})
    if target.loader == FORGE:
        return frozenset({FORGE})
    if target.loader == NEOFORGE:
        if target.game_version in NEOFORGE_LOADS_FORGE:
            return frozenset({NEOFORGE, FORGE})
        return frozenset({NEOFORGE})
    # A game without a loader takes a mod only as its datapack file (Terralith, R2.1)
    return DATAPACK_LOADERS


def multi_loader(version: Version) -> bool:
    """A file built for several mod loaders lists the dependencies of all of them."""
    return len(MOD_LOADERS.intersection(version.loaders)) > 1


def serves(project: Project, target: Target) -> bool:
    """Whether the project has any file at all for the target's loader (any game version).

    Modrinth records dependencies per file, not per loader: a Fabric + NeoForge file may
    require a NeoForge-only library. Such a dependency is skipped for a Fabric game.
    """
    accepted = accepted_loaders(target, project.project_type)
    return any(accepted.intersection(version.loaders) for version in project.versions)


def needs_loader(target: Target, project_type: str) -> bool:
    """A mod in a vanilla game: without a datapack file it cannot run at all."""
    return project_type == "mod" and target.loader == VANILLA


@dataclass(frozen=True)
class ShaderEngine:
    """What a shader version needs on top of the game: a mod (by slug) or a manual step."""

    mod: str | None = None
    warning: str | None = None


def shader_engine(version: Version, target: Target) -> ShaderEngine:
    """Iris on Fabric / Quilt / NeoForge, Oculus on Forge, Canvas on Fabric / Quilt.

    Modrinth does not record this as a dependency (docs/sources.md: shaders have none), so
    without the rule a player would download a shader that never loads.
    """
    loaders = set(version.loaders)
    if target.loader == VANILLA:
        if VANILLA in loaders:
            return ShaderEngine()
        return ShaderEngine(warning="optifine_manual")
    if "iris" in loaders:
        if target.loader in {FABRIC, QUILT, NEOFORGE}:
            return ShaderEngine(mod="iris")
        if target.loader == FORGE:
            return ShaderEngine(mod="oculus")
    if "canvas" in loaders and target.loader in {FABRIC, QUILT}:
        return ShaderEngine(mod="canvas")
    if VANILLA in loaders:
        return ShaderEngine()
    return ShaderEngine(warning="optifine_manual")
