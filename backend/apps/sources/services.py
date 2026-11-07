"""Sync of source metadata that belongs to no domain app: Minecraft versions."""

from django.conf import settings

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


def sync_game_versions(*, client: ModrinthClient, run: SyncCounter) -> None:
    """Upserts every version Modrinth knows; idempotent, unknown types are skipped."""
    known = {item.version: item for item in GameVersion.objects.all()}
    for item in client.get_game_versions():
        if item.version_type not in GameVersion.Type.values:
            run.skipped += 1
            continue
        values = {
            "version_type": item.version_type,
            "released_at": item.date,
            "is_major": item.major,
            "is_supported": is_supported(item.version, item.version_type),
        }
        current = known.get(item.version)
        if current is None:
            GameVersion.objects.create(version=item.version, **values)
            run.created += 1
        elif any(getattr(current, name) != value for name, value in values.items()):
            GameVersion.objects.filter(pk=item.version).update(**values)
            run.updated += 1
        else:
            run.unchanged += 1


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
