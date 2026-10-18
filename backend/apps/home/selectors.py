"""Home page blocks and tops: which objects to show is cached, viewer state is not."""

from collections.abc import Callable
from datetime import timedelta

from django.core.cache import cache
from django.db.models import Count, F, OuterRef, QuerySet, Subquery, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.core.kinds import Viewer, get_kind
from apps.library.models import Download, Favorite
from apps.mods import selectors as mods
from apps.servers import selectors as servers
from apps.skins import selectors as skins
from apps.social.models import Like, Review

HOME_TTL = 5 * 60
TOP_TTL = 10 * 60
TOP_LIMIT = 24
FOR_YOU_LIMIT = 8
ONLINE_LIMIT = 5


def _cached_ids(key: str, ttl: int, build: Callable[[], QuerySet]) -> list[int]:
    ids = cache.get(key)
    if ids is None:
        ids = list(build().values_list("pk", flat=True))
        cache.set(key, ids, ttl)
    return ids


def _in_order(queryset: QuerySet, ids: list[int]) -> list:
    by_pk = queryset.in_bulk(ids)
    return [by_pk[pk] for pk in ids if pk in by_pk]


def for_you(*, viewer: Viewer, game_version: str = "", loader: str = "") -> list:
    """Popular mods for the player's version and loader; without a profile — this week's best."""

    def build() -> QuerySet:
        queryset = mods.catalog()
        if game_version:
            queryset = queryset.filter(game_versions__contains=[game_version])
        if loader and loader != "vanilla":
            queryset = queryset.filter(project_type="mod", loaders__contains=[loader])
        return queryset.order_by("-trend_score", "-modrinth_downloads")[:FOR_YOU_LIMIT]

    key = f"home:for-you:{game_version}:{loader}"
    return _in_order(mods.catalog(viewer), _cached_ids(key, HOME_TTL, build))


def skin_of_week(*, viewer: Viewer):
    """The skin with the highest trend among those published in the last 7 days (or any)."""

    def build() -> QuerySet:
        recent = skins.catalog().filter(published_at__gte=timezone.now() - timedelta(days=7))
        source = recent if recent.exists() else skins.catalog()
        return source.order_by("-trend_score", "-likes_count", "-published_at")[:1]

    found = _in_order(skins.catalog(viewer), _cached_ids("home:skin-of-week", HOME_TTL, build))
    return found[0] if found else None


def servers_online(*, viewer: Viewer) -> list:
    def build() -> QuerySet:
        return (
            servers.with_live(servers.catalog())
            .filter(live_online=True)
            .order_by(F("live_players").desc(nulls_last=True))[:ONLINE_LIMIT]
        )

    return _in_order(servers.catalog(viewer), _cached_ids("home:servers-online", HOME_TTL, build))


def new_skins(*, viewer: Viewer, limit: int = 4) -> list:
    def build() -> QuerySet:
        return skins.catalog().order_by("-published_at")[:limit]

    return _in_order(skins.catalog(viewer), _cached_ids("home:new-skins", HOME_TTL, build))


def new_servers(*, viewer: Viewer, limit: int = 3) -> list:
    def build() -> QuerySet:
        return servers.catalog().order_by("-published_at")[:limit]

    return _in_order(servers.catalog(viewer), _cached_ids("home:new-servers", HOME_TTL, build))


# Tops

CATALOGS = {"mod": mods.catalog, "skin": skins.catalog, "server": servers.catalog}
ALL_TIME = {
    "mod": ["-score", "-modrinth_downloads"],
    "skin": ["-likes_count", "-downloads_count"],
    "server": ["-score", "-favorites_count"],
}


def _monthly(queryset: QuerySet, kind_name: str) -> QuerySet:
    """Likes, saves, reviews (and mod downloads) of the last 30 days, weighted like trends."""
    since = timezone.now() - timedelta(days=30)
    kind = get_kind(kind_name)
    target = {
        "content_type": kind.content_type,
        "object_id": OuterRef("pk"),
        "created_at__gte": since,
    }

    def count(model, field: str = "object_id", **filters) -> Coalesce:
        rows = model.objects.filter(**filters).values(field).annotate(n=Count("pk")).values("n")[:1]
        return Coalesce(Subquery(rows), Value(0))

    # Trend weights ×2 to stay in integers: like 2, save 4, review 6, download 1
    month = (
        2 * count(Like, **target)
        + 4 * count(Favorite, **target)
        + 6 * count(Review, **target, status=Review.Status.PUBLISHED)
    )
    if kind_name == "mod":
        month = month + count(
            Download, field="project_id", project_id=OuterRef("pk"), created_at__gte=since
        )
    return queryset.annotate(month_score=month).filter(month_score__gt=0)


def top(*, kind: str, period: str, viewer: Viewer) -> list:
    def build() -> QuerySet:
        queryset = CATALOGS[kind]()
        if period == "week":
            return queryset.filter(trend_score__gt=0).order_by("-trend_score")[:TOP_LIMIT]
        if period == "month":
            return _monthly(queryset, kind).order_by("-month_score")[:TOP_LIMIT]
        return queryset.order_by(*ALL_TIME[kind])[:TOP_LIMIT]

    ids = _cached_ids(f"top:{kind}:{period}", TOP_TTL, build)
    return _in_order(CATALOGS[kind](viewer), ids)
