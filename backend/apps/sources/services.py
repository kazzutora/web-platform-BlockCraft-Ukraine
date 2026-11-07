"""Sync of source metadata that belongs to no domain app: Minecraft versions."""

from django.conf import settings
from django.db import transaction

from apps.core.versions import is_release, version_key

from .clients.modrinth import ModrinthClient
from .models import GameVersion
from .runs import SyncCounter

#: Oldest release line we sync files for; older ones only via SUPPORTED_LEGACY_VERSIONS
OLDEST_SUPPORTED = (1, 16)


def is_supported(version: str, version_type: str) -> bool:
    if version_type != GameVersion.Type.RELEASE or not is_release(version):
        return False
    return version_key(version) >= OLDEST_SUPPORTED or version in settings.SUPPORTED_LEGACY_VERSIONS


FIELDS = ("version_type", "released_at", "is_major", "is_supported")


def sync_game_versions(*, client: ModrinthClient, run: SyncCounter) -> None:
    """Upserts every version Modrinth knows in two bulk queries; idempotent.

    A version Modrinth no longer lists (e.g. one kept from a player profile) stops being
    supported instead of staying in «Моя гра» forever.
    """
    known = {item.version: item for item in GameVersion.objects.all()}
    seen: set[str] = set()
    new: list[GameVersion] = []
    changed: list[GameVersion] = []
    for item in client.get_game_versions():
        if item.version_type not in GameVersion.Type.values:
            run.skipped += 1
            continue
        seen.add(item.version)
        values = {
            "version_type": item.version_type,
            "released_at": item.date,
            "is_major": item.major,
            "is_supported": is_supported(item.version, item.version_type),
        }
        current = known.get(item.version)
        if current is None:
            new.append(GameVersion(version=item.version, **values))
        elif any(getattr(current, name) != value for name, value in values.items()):
            for name, value in values.items():
                setattr(current, name, value)
            changed.append(current)
        else:
            run.unchanged += 1
    for version, current in known.items():
        if version not in seen and current.is_supported:
            current.is_supported = False
            changed.append(current)
    with transaction.atomic():
        GameVersion.objects.bulk_create(new, batch_size=500)
        GameVersion.objects.bulk_update(changed, FIELDS, batch_size=500)
    run.created += len(new)
    run.updated += len(changed)


class NoGameVersionsError(RuntimeError):
    """Catalog syncs need the supported versions: without them they would take every file."""


def supported_game_versions() -> list[str]:
    """Supported versions, newest first."""
    versions = list(GameVersion.objects.supported().values_list("version", flat=True))
    if not versions:
        raise NoGameVersionsError(
            "No game versions yet: run `make sync s=modrinth j=game_versions` first."
        )
    return versions
