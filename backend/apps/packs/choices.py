"""Fixed lists behind the pack catalog and the .mrpack format."""

from django.db import models

from apps.core.game import Loader


class PackLoader(models.TextChoices):
    """Loaders a modpack runs on: vanilla has nothing to install mods into."""

    FABRIC = Loader.FABRIC.value, Loader.FABRIC.label
    FORGE = Loader.FORGE.value, Loader.FORGE.label
    NEOFORGE = Loader.NEOFORGE.value, Loader.NEOFORGE.label
    QUILT = Loader.QUILT.value, Loader.QUILT.label


#: Players add mods one by one; imported modpacks may be bigger
MAX_ITEMS = 300

#: `dependencies` keys of modrinth.index.json
MRPACK_LOADER_KEYS = {
    PackLoader.FABRIC: "fabric-loader",
    PackLoader.FORGE: "forge",
    PackLoader.NEOFORGE: "neoforge",
    PackLoader.QUILT: "quilt-loader",
}
