from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.schema import error_responses

from . import services
from .serializers import ResolutionSerializer, ResolveRequestSerializer, resolution_data
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
