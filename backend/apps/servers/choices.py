"""Fixed lists behind the server catalog filters."""

from django.db import models


class Edition(models.TextChoices):
    JAVA = "java", "Java"
    BEDROCK = "bedrock", "Bedrock"
    BOTH = "both", "Java і Bedrock"


class Mode(models.TextChoices):
    SURVIVAL = "survival", "Виживання"
    SMP = "smp", "SMP"
    CREATIVE = "creative", "Творчий"
    ANARCHY = "anarchy", "Анархія"
    RP = "rp", "Рольова гра"
    MINIGAMES = "minigames", "Мініігри"
    SKYBLOCK = "skyblock", "SkyBlock"
    PVP = "pvp", "PvP"
    MODDED = "modded", "З модами"
    HARDCORE = "hardcore", "Хардкор"


MAX_MODES = 5


class Language(models.TextChoices):
    UK = "uk", "Українська"
    MULTI = "multi", "Кілька мов"
    EN = "en", "Англійська"


DEFAULT_PORTS = {Edition.JAVA: 25565, Edition.BEDROCK: 19132, Edition.BOTH: 25565}
