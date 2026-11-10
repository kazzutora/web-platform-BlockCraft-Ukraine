from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.schema import error_responses
from apps.mods import identify

from . import services
from .serializers import (
    IdentifyRequestSerializer,
    IdentifyResponseSerializer,
    ResolutionSerializer,
    ResolveRequestSerializer,
    UpdatesRequestSerializer,
    UpdatesResponseSerializer,
    project_ref,
    resolution_data,
    version_ref,
)
from .types import Target


class ResolveView(APIView):
    """What to install for any set of catalog projects; guests too (tech.md 7)."""

    permission_classes = [AllowAny]
    # Up to 300 projects with all their versions: limited for guests and players alike
    throttle_scope = "compat"

    @extend_schema(
        operation_id="compat_resolve",
        request=ResolveRequestSerializer,
        responses={200: ResolutionSerializer, **error_responses(400)},
        description=(
            "Up to 300 projects. `incomplete` — some dependencies are being imported from "
            "Modrinth, ask again in a few seconds."
        ),
        tags=["compat"],
    )
    def post(self, request: Request) -> Response:
        body = ResolveRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        resolved = services.resolve_slugs(
            items=[(item["slug"], item.get("version_id") or None) for item in data["items"]],
            target=Target(data["game_version"], data["loader"]),
        )
        return Response(resolution_data(resolved))


class IdentifyView(APIView):
    """/import: which mods these hashes are and what game they were made for."""

    permission_classes = [AllowAny]
    throttle_scope = "compat"

    @extend_schema(
        operation_id="compat_identify",
        request=IdentifyRequestSerializer,
        responses={200: IdentifyResponseSerializer, **error_responses(400)},
        description="Only SHA-1 hashes: files never leave the player's computer.",
        tags=["compat"],
    )
    def post(self, request: Request) -> Response:
        body = IdentifyRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        names = {item["hash"].lower(): item["name"] for item in body.validated_data["files"]}
        found = identify.identify(names)
        guess = found.guess.target
        return Response(
            IdentifyResponseSerializer(
                {
                    "known": [
                        {
                            "hash": sha1,
                            "name": names.get(sha1, ""),
                            "project": project_ref(row.project),
                            "version": version_ref(row),
                            "game_versions": row.game_versions,
                            "loaders": row.loaders,
                        }
                        for sha1, row in found.known.items()
                    ],
                    "unknown": [
                        {"hash": sha1, "name": names.get(sha1, "")} for sha1 in found.unknown
                    ],
                    "guess": {"game_version": guess.game_version, "loader": guess.loader}
                    if guess
                    else None,
                    "fitting": found.guess.fitting,
                    "identified": found.guess.identified,
                    "source_unavailable": found.source_unavailable,
                }
            ).data
        )


class UpdatesView(APIView):
    """/import: what of these files can move to another game, and to which version."""

    permission_classes = [AllowAny]
    throttle_scope = "compat"

    @extend_schema(
        operation_id="compat_updates",
        request=UpdatesRequestSerializer,
        responses={200: UpdatesResponseSerializer, **error_responses(400)},
        tags=["compat"],
    )
    def post(self, request: Request) -> Response:
        body = UpdatesRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        target = Target(data["game_version"], data["loader"])
        found = identify.identify(item["hash"] for item in data["files"])
        rows, unavailable = identify.updates(found.known, target)
        files = []
        for update in rows:
            latest = update.latest
            status = update.status
            files.append(
                {
                    "hash": update.sha1,
                    "project": project_ref(update.current.project),
                    "current": version_ref(update.current),
                    "latest": version_ref(latest) if latest else None,
                    "status": status,
                }
            )
        return Response(
            UpdatesResponseSerializer(
                {
                    "target": {"game_version": target.game_version, "loader": target.loader},
                    "files": files,
                    "source_unavailable": unavailable,
                }
            ).data
        )
