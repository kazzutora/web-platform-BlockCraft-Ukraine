from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.game import game_context
from apps.core.schema import error_responses
from apps.servers import status as live_status

from . import selectors
from .serializers import HomeSerializer, TopQuerySerializer, TopSerializer


def _game_profile(request: Request) -> tuple[str, str]:
    context = game_context(request)
    return context.game_version, context.loader


class HomeView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="home",
        responses={200: HomeSerializer},
        description=(
            "Home page blocks (tech.md 10.4) for «Моя гра» of the viewer: mods and packs that "
            "fit it; without it — this week's popular. Which objects to show is cached."
        ),
    )
    def get(self, request: Request) -> Response:
        viewer = request.user
        game_version, loader = _game_profile(request)
        personal = bool(game_version or loader)
        game = {"game_version": game_version, "loader": loader} if personal else {}
        online = selectors.servers_online(viewer=viewer)
        skin = selectors.skin_of_day(viewer=viewer)
        data = {
            "for_you": {
                "basis": "profile" if personal else "popular",
                "game_version": game_version,
                "loader": loader,
                "mods": selectors.for_you(viewer=viewer, **game),
            },
            "packs": selectors.ready_packs(viewer=viewer, **game),
            "servers_online": online,
            "skin_of_day": skin,
            "skins": selectors.more_skins(viewer=viewer, without=skin.pk if skin else None),
        }
        context = {"request": request, "live": live_status.get_many(s.pk for s in online)}
        return Response(HomeSerializer(data, context=context).data)


class TopView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="top",
        parameters=[TopQuerySerializer],
        responses={200: TopSerializer, **error_responses(400)},
        description="Week: trend; month: weighted events of 30 days; all: rating. 24 items.",
    )
    def get(self, request: Request) -> Response:
        query = TopQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        kind, period = query.validated_data["kind"], query.validated_data["period"]
        items = selectors.top(kind=kind, period=period, viewer=request.user)
        data = {
            "kind": kind,
            "period": period,
            "mods": items if kind == "mod" else [],
            "packs": items if kind == "pack" else [],
            "skins": items if kind == "skin" else [],
            "servers": items if kind == "server" else [],
        }
        context = {"request": request}
        if kind == "server":
            context["live"] = live_status.get_many(s.pk for s in items)
        return Response(TopSerializer(data, context=context).data)
