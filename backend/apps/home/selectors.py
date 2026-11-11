"""Home page blocks and tops: which objects to show is cached, viewer state is not."""

from collections.abc import Callable
from datetime import date, timedelta

from django.core.cache import cache
from django.db.models import Count, F, OuterRef, QuerySet, Subquery, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.core.game import Loader
from apps.core.kinds import Viewer, get_kind
from apps.library.models import Download, Favorite
from apps.mods import selectors as mods
from apps.mods.models import ProjectType
from apps.packs import selectors as packs
from apps.packs.choices import PackLoader
from apps.servers import selectors as servers
from apps.skins import selectors as skins
from apps.social.models import Review

HOME_TTL = 5 * 60
DAY_TTL = 25 * 60 * 60
TOP_TTL = 10 * 60
TOP_LIMIT = 24
# The blocks of tech.md 10.4
FOR_YOU_LIMIT = 8
PACKS_LIMIT = 4
ONLINE_LIMIT = 5
SKINS_LIMIT = 6
SKIN_OF_DAY_POOL = 30
HOME_LANGUAGE = "uk"


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
    """Popular mods for «Моя гра» (the catalog's rule); without it — this week's best.

    With a mod loader only mods are shown; a vanilla game gets what runs without one
    (resource packs, shaders, datapacks, mods that ship as datapacks).
    """

    def build() -> QuerySet:
        queryset = mods.catalog()
        if game_version:
            queryset = queryset.filter(game_versions__contains=[game_version])
        if loader:
            queryset = queryset.filter(mods.for_loader(loader))
            if loader != Loader.VANILLA:
                queryset = queryset.filter(project_type=ProjectType.MOD)
        return queryset.order_by("-trend_score", "-modrinth_downloads")[:FOR_YOU_LIMIT]

    key = f"home:for-you:{game_version}:{loader}"
    return _in_order(mods.catalog(viewer), _cached_ids(key, HOME_TTL, build))


def ready_packs(*, viewer: Viewer, game_version: str = "", loader: str = "") -> list:
    """«Готові збірки»: for «Моя гра» like the packs catalog (vanilla — any pack loader)."""

    def build() -> QuerySet:
        queryset = packs.catalog()
        if game_version:
            queryset = queryset.filter(game_version=game_version)
        if loader in PackLoader.values:
            queryset = queryset.filter(loader=loader)
        return queryset.order_by("-trend_score", "-score", "-modrinth_downloads")[:PACKS_LIMIT]

    key = f"home:packs:{game_version}:{loader}"
    return _in_order(packs.catalog(viewer), _cached_ids(key, HOME_TTL, build))


def servers_online(*, viewer: Viewer) -> list:
    """«Сервери онлайн · українською»: Ukrainian-speaking servers up now, busiest first."""

    def build() -> QuerySet:
        return (
            servers.with_live(servers.catalog().filter(languages__contains=[HOME_LANGUAGE]))
            .filter(live_online=True)
            .order_by(F("live_players").desc(nulls_last=True))[:ONLINE_LIMIT]
        )

    return _in_order(servers.catalog(viewer), _cached_ids("home:servers-online", HOME_TTL, build))


def skin_of_day(*, viewer: Viewer, today: date | None = None):
    """«Скін дня»: one of the most liked skins, a different one each day (same for everyone)."""
    today = today or timezone.localdate()

    def build() -> QuerySet:
        # The pool in a stable order: a trend that moves does not shift today's pick
        pool = sorted(
            skins.catalog()
            .order_by("-trend_score", "-favorites_count", "-downloads_count", "-created_at")
            .values_list("pk", flat=True)[:SKIN_OF_DAY_POOL]
        )
        picked = pool[today.toordinal() % len(pool)] if pool else None
        return skins.catalog().filter(pk=picked)

    # The key names the day and outlives it: one pick for everyone all day long
    key = f"home:skin-of-day:{today.isoformat()}"
    found = _in_order(skins.catalog(viewer), _cached_ids(key, DAY_TTL, build))
    return found[0] if found else None


def more_skins(*, viewer: Viewer, without: int | None) -> list:
    """Six skins next to the skin of the day: the newest ones."""

    def build() -> QuerySet:
        return skins.catalog().order_by("-created_at")[: SKINS_LIMIT + 1]

    ids = [pk for pk in _cached_ids("home:skins", HOME_TTL, build) if pk != without]
    return _in_order(skins.catalog(viewer), ids[:SKINS_LIMIT])


# Tops

CATALOGS = {
    "mod": mods.catalog,
    "pack": packs.catalog,
    "skin": skins.catalog,
    "server": servers.catalog,
}
ALL_TIME = {
    "mod": ["-score", "-modrinth_downloads"],
    "pack": ["-score", "-downloads_count", "-modrinth_downloads"],
    "skin": ["-favorites_count", "-downloads_count"],
    "server": ["-score", "-favorites_count"],
}


def _monthly(queryset: QuerySet, kind_name: str) -> QuerySet:
    """Saves, reviews (and mod downloads) of the last 30 days, weighted like trends."""
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

    # Trend weights ×2 to stay in integers: save 4, review 6, download 1
    month = 4 * count(Favorite, **target) + 6 * count(
        Review, **target, status=Review.Status.PUBLISHED
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
