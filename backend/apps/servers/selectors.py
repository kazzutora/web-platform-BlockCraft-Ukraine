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
    queryset = queryset.select_related("author")
    return with_viewer_state(queryset, viewer=viewer or AnonymousUser(), kind=get_kind("server"))


def catalog(viewer: Viewer | None = None) -> QuerySet[Server]:
    """Published servers with the viewer's favorite/review state annotated."""
    return _with_state(Server.objects.published(), viewer)


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
    """Published servers for everyone; the owner and moderators also see the rest."""
    viewer = viewer or AnonymousUser()
    queryset = Server.objects.all()
    if not viewer.is_authenticated:
        queryset = queryset.filter(status=Server.Status.PUBLISHED)
    elif not viewer.is_moderator:
        queryset = queryset.filter(Q(status=Server.Status.PUBLISHED) | Q(author=viewer))
    try:
        return _with_state(queryset, viewer).get(slug=slug)
    except Server.DoesNotExist as error:
        raise Http404 from error


def my_servers(user: User) -> QuerySet[Server]:
    return _with_state(Server.objects.filter(author=user), user).order_by("-created_at")


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
