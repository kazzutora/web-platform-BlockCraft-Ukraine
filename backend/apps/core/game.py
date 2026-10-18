"""Minecraft vocabulary shared by profiles, mods and servers."""

from django.db import models


class Loader(models.TextChoices):
    FABRIC = "fabric", "Fabric"
    FORGE = "forge", "Forge"
    NEOFORGE = "neoforge", "NeoForge"
    QUILT = "quilt", "Quilt"
    VANILLA = "vanilla", "Vanilla"


class Edition(models.TextChoices):
    JAVA = "java", "Java"
    BEDROCK = "bedrock", "Bedrock"


# Release versions offered in the profile, newest first (Modrinth tag list, 2026-10).
# Stage 3 keeps the catalog in sync with Modrinth; this list only bounds user input.
GAME_VERSIONS: tuple[str, ...] = (
    "26.3", "26.2", "26.1.2", "26.1.1", "26.1",
    "1.21.11", "1.21.10", "1.21.9", "1.21.8", "1.21.7", "1.21.6", "1.21.5", "1.21.4",
    "1.21.3", "1.21.2", "1.21.1", "1.21",
    "1.20.6", "1.20.5", "1.20.4", "1.20.3", "1.20.2", "1.20.1", "1.20",
    "1.19.4", "1.19.3", "1.19.2", "1.19.1", "1.19",
    "1.18.2", "1.18.1", "1.18", "1.17.1", "1.17",
    "1.16.5", "1.16.4", "1.16.3", "1.16.2", "1.16.1", "1.16",
    "1.12.2", "1.8.9",
)  # fmt: skip

GAME_VERSION_CHOICES = [(version, version) for version in GAME_VERSIONS]
