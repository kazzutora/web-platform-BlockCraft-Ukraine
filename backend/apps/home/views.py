from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.schema import error_responses
from apps.servers import status as live_status

from . import selectors
from .serializers import HomeSerializer, TopQuerySerializer, TopSerializer


def _game_profile(request: Request) -> tuple[str, str]:
    profile = getattr(request.user, "game_profile", None) if request.user.is_authenticated else None
    return (profile.game_version, profile.loader) if profile else ("", "")


class HomeView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="home",
        responses={200: HomeSerializer},
        description="Home page blocks. Which objects to show is cached for 5 minutes.",
    )
    def get(self, request: Request) -> Response:
        viewer = request.user
        game_version, loader = _game_profile(request)
        personal = bool(game_version or (loader and loader != "vanilla"))
        online = selectors.servers_online(viewer=viewer)
        new_servers = selectors.new_servers(viewer=viewer)
        data = {
            "for_you": {
                "basis": "profile" if personal else "popular",
                "game_version": game_version,
                "loader": loader,
                "mods": selectors.for_you(viewer=viewer, game_version=game_version, loader=loader)
                if personal
                else selectors.for_you(viewer=viewer),
            },
            "skin_of_week": selectors.skin_of_week(viewer=viewer),
            "servers_online": online,
            "new_skins": selectors.new_skins(viewer=viewer),
            "new_servers": new_servers,
        }
        context = {
            "request": request,
            "live": live_status.get_many(s.pk for s in [*online, *new_servers]),
        }
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
            "skins": items if kind == "skin" else [],
            "servers": items if kind == "server" else [],
        }
        context = {"request": request}
        if kind == "server":
            context["live"] = live_status.get_many(s.pk for s in items)
        return Response(TopSerializer(data, context=context).data)
