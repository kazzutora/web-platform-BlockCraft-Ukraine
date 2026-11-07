from typing import Any

from django.core.cache import cache

from apps.core.game import Loader

from .models import GameVersion

META_KEY = "sources:meta"
META_TTL = 10 * 60


def meta() -> dict[str, Any]:
    """What every form and filter needs: supported versions, loaders, categories (GET /meta)."""
    return cache.get_or_set(META_KEY, _build_meta, META_TTL)


def _build_meta() -> dict[str, Any]:
    from apps.mods.models import Category

    return {
        "game_versions": list(GameVersion.objects.supported()),
        "loaders": list(Loader.values),
        "categories": list(Category.objects.all()),
    }


def forget_meta() -> None:
    cache.delete(META_KEY)
