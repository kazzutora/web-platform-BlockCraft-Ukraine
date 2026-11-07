from apps.sources.models import GameVersion
from apps.sources.services import is_supported

from .recorded import load


def supported_game_versions() -> list[str]:
    """Creates the supported versions of the recorded `/tag/game_version` answer."""
    rows = [
        GameVersion(
            version=item["version"],
            version_type=item["version_type"],
            released_at=item["date"],
            is_major=item["major"],
            is_supported=True,
        )
        for item in load("modrinth", "tag_game_version")
        if is_supported(item["version"], item["version_type"])
    ]
    GameVersion.objects.bulk_create(rows, ignore_conflicts=True)
    return [row.version for row in rows]
