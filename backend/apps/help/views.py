from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.compat.serializers import resolution_data
from apps.compat.types import Target
from apps.core.game import game_context
from apps.core.schema import error_responses

from . import selectors, services
from .serializers import (
    CrashRequestSerializer,
    CrashResponseSerializer,
    GoalsPreviewSerializer,
    GoalsRequestSerializer,
    SavedPackSerializer,
)


def _target(request: Request, data: dict) -> Target:
    """The request's game wins, then «Моя гра»."""
    game = game_context(request)
    return Target(data.get("game_version") or game.game_version, data.get("loader") or game.loader)


class CrashView(APIView):
    """/help/crash: the mods a crash log names, matched with the catalog."""

    permission_classes = [AllowAny]
    throttle_scope = "help"

    @extend_schema(
        operation_id="help_crash",
        request=CrashRequestSerializer,
        responses={200: CrashResponseSerializer, **error_responses(400, 429)},
        description=(
            "The browser parses the log and sends only mod ids and names; this answers which "
            "of them are in the catalog and the latest stable loader for the log's game."
        ),
        tags=["help"],
    )
    def post(self, request: Request) -> Response:
        body = CrashRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        found = selectors.match_mods(mods_found=data["mods"], viewer=request.user)
        release = selectors.loader_release(
            loader=data.get("loader", ""), game_version=data.get("game_version", "")
        )
        payload = {
            "mods": [{"id": mod_id, "project": project} for mod_id, project in found.items()],
            "loader_release": release,
        }
        return Response(CrashResponseSerializer(payload, context={"request": request}).data)


class GoalsPreviewView(APIView):
    """/help/goal: what a pack for these goals would be, without saving anything."""

    permission_classes = [AllowAny]
    throttle_scope = "help"

    @extend_schema(
        operation_id="help_goals_preview",
        request=GoalsRequestSerializer,
        responses={200: GoalsPreviewSerializer, **error_responses(400, 429)},
        description=(
            "Real catalog projects for each goal that fit the game (default: «Моя гра»), "
            "with dependencies and conflicts from the compat engine. `needs_mod_loader` — "
            "the game has no mod loader."
        ),
        tags=["help"],
    )
    def post(self, request: Request) -> Response:
        body = GoalsRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        found = services.preview(
            goals=body.validated_data["goals"], target=_target(request, body.validated_data)
        )
        payload = {
            "target": found.target,
            "choices": found.choices,
            "resolution": resolution_data(found.resolved),
        }
        return Response(GoalsPreviewSerializer(payload).data)


class GoalsPackView(APIView):
    """Saves the preview as the player's private draft pack."""

    permission_classes = [IsAuthenticated]
    throttle_scope = "pack_edits"

    @extend_schema(
        operation_id="help_goals_pack",
        request=GoalsRequestSerializer,
        responses={201: SavedPackSerializer, **error_responses(400, 401, 429)},
        description="A private draft with the picked projects; open it in the constructor.",
        tags=["help"],
    )
    def post(self, request: Request) -> Response:
        body = GoalsRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        pack = services.save_pack(
            user=request.user,
            goals=body.validated_data["goals"],
            target=_target(request, body.validated_data),
        )
        return Response(SavedPackSerializer({"slug": pack.slug}).data, status.HTTP_201_CREATED)
