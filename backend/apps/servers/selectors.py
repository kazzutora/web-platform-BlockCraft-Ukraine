from datetime import timedelta

from django.contrib.auth.models import AnonymousUser
from django.db.models import Avg, Count, Max, OuterRef, Q, QuerySet, Subquery
from django.db.models.functions import TruncHour
from django.http import Http404
from django.utils import timezone

from apps.accounts.models import User
from apps.core.kinds import Viewer, get_kind
from apps.social.selectors import with_viewer_state

from . import status
from .models import Server, ServerSnapshot

RANGES = {"24h": timedelta(hours=24), "7d": timedelta(days=7)}


def _with_state(queryset: QuerySet[Server], viewer: Viewer | None) -> QuerySet[Server]:
    queryset = queryset.select_related("owner", "required_pack__author")
    return with_viewer_state(queryset, viewer=viewer or AnonymousUser(), kind=get_kind("server"))


def catalog(viewer: Viewer | None = None) -> QuerySet[Server]:
    """Listed servers with the viewer's favorite/review state annotated."""
    return _with_state(Server.objects.listed(), viewer)


def with_live(queryset: QuerySet[Server]) -> QuerySet[Server]:
    """Latest snapshot of the last 15 minutes (as long as the Redis status lives)."""
    fresh = ServerSnapshot.objects.filter(
        server=OuterRef("pk"), ts__gte=timezone.now() - timedelta(seconds=status.TTL)
    ).order_by("-ts")
    return queryset.annotate(
        live_online=Subquery(fresh.values("is_online")[:1]),
        live_players=Subquery(fresh.values("players_online")[:1]),
    )


def get_server(*, slug: str, viewer: Viewer | None = None) -> Server:
    """Listed servers for everyone; whoever claims or owns one and moderators see the rest."""
    viewer = viewer or AnonymousUser()
    queryset = Server.objects.all()
    if not viewer.is_authenticated:
        queryset = Server.objects.listed()
    elif not viewer.is_moderator:
        queryset = queryset.filter(
            Q(pk__in=Server.objects.listed()) | Q(owner=viewer) | Q(claimant=viewer)
        )
    try:
        return _with_state(queryset, viewer).get(slug=slug)
    except Server.DoesNotExist as error:
        raise Http404 from error


def my_servers(user: User) -> QuerySet[Server]:
    mine = Server.objects.filter(Q(owner=user) | Q(claimant=user))
    return _with_state(mine, user).order_by("-created_at")


#: Below this the «українська» default would show an almost empty catalog
UK_DEFAULT_MIN = 5


def default_language() -> str:
    """«uk» while there are enough Ukrainian-speaking servers, else no language filter."""
    count = Server.objects.listed().filter(languages__contains=["uk"]).count()
    return "uk" if count >= UK_DEFAULT_MIN else ""


def facets() -> dict[str, list[str]]:
    """Languages and countries the listed servers have (for /meta and the filters)."""
    rows = Server.objects.listed().values_list("languages", "country")
    languages = sorted({code for codes, _ in rows for code in codes})
    countries = sorted({country for _, country in rows if country})
    return {"languages": languages, "countries": countries}


def stats(*, server: Server, range_name: str) -> dict:
    """Chart points (24h — every ping, 7d — hourly averages), uptime and peak of the range."""
    since = timezone.now() - RANGES[range_name]
    snapshots = server.snapshots.filter(ts__gte=since)
    totals = snapshots.aggregate(
        total=Count("pk"), online=Count("pk", filter=Q(is_online=True)), peak=Max("players_online")
    )
    if range_name == "24h":
        points = [
            {"ts": ts, "players": players if online else 0, "is_online": online}
            for ts, players, online in snapshots.order_by("ts").values_list(
                "ts", "players_online", "is_online"
            )
        ]
    else:
        rows = (
            snapshots.annotate(hour=TruncHour("ts"))
            .values("hour")
            .annotate(
                players=Avg("players_online", filter=Q(is_online=True)),
                online=Count("pk", filter=Q(is_online=True)),
            )
            .order_by("hour")
        )
        points = [
            {
                "ts": row["hour"],
                "players": round(row["players"] or 0, 1),
                "is_online": row["online"] > 0,
            }
            for row in rows
        ]
    uptime = round(totals["online"] / totals["total"] * 100, 1) if totals["total"] else None
    return {
        "range": range_name,
        "uptime_percent": uptime,
        "peak_players": totals["peak"] or 0,
        "points": points,
    }


def pack_for_joining(server: Server):
    """The pack to take, while anyone may see it (published, «усім»); else None."""
    from apps.packs.models import Visibility

    pack = server.required_pack
    if pack is None or pack.status != pack.Status.PUBLISHED:
        return None
    return pack if pack.visibility == Visibility.PUBLIC else None


def join(*, server: Server, game) -> dict:
    """«Щоб зайти»: what the viewer needs and whether their «Моя гра» already fits."""
    from .models import ContentKind

    pack = pack_for_joining(server)
    if server.content_kind == ContentKind.MODDED or pack is not None:
        fits = None
        if pack is not None and game.is_set:
            fits = (not game.game_version or game.game_version == pack.game_version) and (
                not game.loader or game.loader == pack.loader
            )
        return {
            "address": server.address,
            "edition": server.edition,
            "kind": ContentKind.MODDED,
            "versions": [pack.game_version] if pack else [],
            "recommended_version": pack.game_version if pack else "",
            "pack": pack,
            "pack_pending": pack is None and bool(server.modpack_project_id),
            "fits_my_game": fits,
        }
    versions = server.supported_versions
    fits = None
    if game.game_version and versions:
        # Client-side mods do not stop anyone joining a vanilla server: the version does
        fits = game.game_version in versions
    return {
        "address": server.address,
        "edition": server.edition,
        "kind": server.content_kind,
        "versions": versions,
        "recommended_version": server.recommended_version,
        "pack": None,
        "pack_pending": False,
        "fits_my_game": fits,
    }
