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
