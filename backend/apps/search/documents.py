"""What goes into the `content` index: one document per searchable object of every kind."""

from collections.abc import Callable
from dataclasses import dataclass

from django.db.models import Model, QuerySet

from apps.core.versions import latest_release
from apps.library.models import Collection
from apps.mods.models import Project
from apps.servers.models import Server
from apps.skins.models import Skin

INDEX_SETTINGS = {
    "searchableAttributes": ["title", "tags", "summary", "author"],
    "filterableAttributes": [
        "kind",
        "project_type",
        "game_versions",
        "loaders",
        "color_bucket",
        "modes",
    ],
    "sortableAttributes": ["score", "trend_score", "published_at", "popularity"],
    # Relevance first; among equally good matches the popular one wins («sodim» → Sodium)
    "rankingRules": [
        "words",
        "typo",
        "proximity",
        "attribute",
        "sort",
        "exactness",
        "popularity:desc",
        "score:desc",
    ],
    "displayedAttributes": ["*"],
}


def _timestamp(value) -> int:
    return int(value.timestamp()) if value else 0


def _base(kind: str, identifier: str, obj: Model, **fields) -> dict:
    return {
        "uid": f"{kind}-{obj.pk}",
        "kind": kind,
        "id": identifier,
        "score": getattr(obj, "score", 0.0),
        "trend_score": getattr(obj, "trend_score", 0.0),
        "published_at": _timestamp(getattr(obj, "published_at", None)),
        "popularity": 0,
        "tags": [],
        "game_versions": [],
        "loaders": [],
        "modes": [],
        "color_bucket": None,
        "project_type": None,
        "author": None,
        "image": None,
        **fields,
    }


def mod_document(project: Project) -> dict:
    categories = list(project.categories.all())
    return _base(
        "mod",
        project.slug,
        project,
        title=project.title,
        summary=project.summary_uk or project.summary,
        tags=[c.slug for c in categories] + [c.name_uk for c in categories],
        game_versions=project.game_versions,
        loaders=project.loaders,
        project_type=project.project_type,
        image=project.icon_url or None,
        popularity=project.modrinth_downloads + project.downloads_count,
        latest_game_version=latest_release(project.game_versions),
    )


def skin_document(skin: Skin) -> dict:
    image = skin.preview or skin.file
    return _base(
        "skin",
        str(skin.pk),
        skin,
        title=skin.title,
        summary="",
        tags=skin.style_tags,
        color_bucket=skin.color_bucket,
        popularity=skin.downloads_count + 10 * (skin.likes_count + skin.favorites_count),
        author=skin.author.nickname,
        image=image.url if image else None,
    )


def server_document(server: Server) -> dict:
    return _base(
        "server",
        server.slug,
        server,
        title=server.name,
        summary=server.description[:300],
        tags=[server.host, server.versions_label],
        modes=server.modes,
        popularity=10 * server.favorites_count + 5 * server.rating_count + server.ip_copies_count,
        author=server.author.nickname,
        image=server.banner.url if server.banner else None,
        address=server.address,
    )


def collection_document(collection: Collection) -> dict:
    return _base(
        "collection",
        str(collection.pk),
        collection,
        title=collection.title,
        summary=collection.description,
        author=collection.owner.nickname,
        items_count=collection.items_count,
        popularity=10 * (collection.likes_count + collection.favorites_count),
    )


@dataclass(frozen=True)
class Source:
    queryset: Callable[[], QuerySet]
    document: Callable[[Model], dict]


# Only what anyone may open is searchable
SOURCES: dict[str, Source] = {
    "mod": Source(lambda: Project.objects.published().prefetch_related("categories"), mod_document),
    "skin": Source(lambda: Skin.objects.published().select_related("author"), skin_document),
    "server": Source(lambda: Server.objects.published().select_related("author"), server_document),
    "collection": Source(
        lambda: Collection.objects.filter(
            visibility=Collection.Visibility.PUBLIC, items_count__gt=0
        ).select_related("owner"),
        collection_document,
    ),
}


def document_for(kind: str, pk: int) -> dict | None:
    """The document of a searchable object, or None if it must leave the index."""
    source = SOURCES.get(kind)
    if source is None:
        return None
    obj = source.queryset().filter(pk=pk).first()
    return source.document(obj) if obj else None
