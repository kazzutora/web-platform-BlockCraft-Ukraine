"""Minimal Modrinth payloads shaped like the real API (fields we read + some we ignore)."""


def project_payload(
    project_id: str = "AANobbMI",
    slug: str = "sodium",
    project_type: str = "mod",
    **overrides,
) -> dict:
    return {
        "id": project_id,
        "slug": slug,
        "project_type": project_type,
        "title": slug.title(),
        "description": f"{slug} description",
        "body": "# Hello\n\n<script>alert(1)</script>Text",
        "categories": ["optimization"],
        "additional_categories": [],
        "loaders": ["fabric", "quilt"],
        "game_versions": ["1.21.1", "26.3", "26w14a"],
        "downloads": 1_000_000,
        "followers": 10,
        "icon_url": f"https://cdn.modrinth.com/data/{project_id}/icon.webp",
        "gallery": [
            {"url": "https://cdn.modrinth.com/a.webp", "featured": False, "ordering": 1},
            {"url": "https://cdn.modrinth.com/b.webp", "featured": True, "ordering": 2},
        ],
        "license": {"id": "MIT", "name": "MIT License", "url": None},
        "source_url": "https://github.com/example",
        "published": "2021-01-03T00:53:34Z",
        "updated": "2026-10-15T17:51:44Z",
        "team": "ignored",
        **overrides,
    }


def version_payload(
    version_id: str = "bAZQdGpg",
    project_id: str = "AANobbMI",
    game_versions: list[str] | None = None,
    loaders: list[str] | None = None,
    version_type: str = "release",
    date: str = "2026-10-01T00:00:00Z",
    dependencies: list[dict] | None = None,
) -> dict:
    return {
        "id": version_id,
        "project_id": project_id,
        "name": f"Version {version_id}",
        "version_number": f"v-{version_id}",
        "version_type": version_type,
        "game_versions": game_versions or ["26.3"],
        "loaders": loaders or ["fabric"],
        "date_published": date,
        "downloads": 5,
        "files": [
            {
                "url": f"https://cdn.modrinth.com/data/{project_id}/{version_id}.jar",
                "filename": f"{version_id}.jar",
                "primary": True,
                "size": 2048,
                "hashes": {"sha1": "a" * 40, "sha512": "b" * 128},
            }
        ],
        "dependencies": dependencies or [],
    }


CATEGORIES = [
    {"name": "optimization", "project_type": "mod", "header": "categories", "icon": "<svg/>"},
    {"name": "low", "project_type": "shader", "header": "performance impact", "icon": ""},
    {"name": "high", "project_type": "shader", "header": "performance impact", "icon": ""},
    {"name": "economy", "project_type": "plugin", "header": "categories", "icon": ""},
]
