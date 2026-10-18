"""Ordering of Minecraft version strings: "1.21.11" > "1.21.4", "26.1" > "1.21.11"."""

import re

_PART = re.compile(r"\d+")
_RELEASE = re.compile(r"^\d+\.\d+(?:\.\d+)?$")


def version_key(version: str) -> tuple[int, ...]:
    """Numeric key; non-release suffixes (snapshots like "24w14a") sort as their numbers."""
    return tuple(int(part) for part in _PART.findall(version)) or (0,)


def is_release(version: str) -> bool:
    """ "1.21.11" and "26.3" are releases; "26w14a", "26.3-rc-2", "1.21-pre1" are not."""
    return bool(_RELEASE.match(version))


def latest_release(versions: list[str]) -> str:
    return max(filter(is_release, versions), key=version_key, default="")


def nearest_versions(target: str, available: list[str], limit: int = 3) -> list[str]:
    """Versions closest to `target`, preferring the same major line, newest first on ties."""
    goal = version_key(target)

    def distance(version: str) -> tuple[int, int, tuple[int, ...]]:
        key = version_key(version)
        same_line = 0 if key[:2] == goal[:2] else 1
        # Compare major / minor / patch; shorter versions simply stop earlier
        gap = sum(
            abs(a - b) * weight for a, b, weight in zip(key, goal, (10_000, 100, 1), strict=False)
        )
        return same_line, gap, tuple(-part for part in key)

    unique = sorted(set(available) - {target}, key=distance)
    return unique[:limit]
