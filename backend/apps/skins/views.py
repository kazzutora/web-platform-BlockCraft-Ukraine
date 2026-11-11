import base64

from django.http import FileResponse
from django.utils.text import get_valid_filename
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.cache import GuestCachedListMixin
from apps.core.exceptions import DomainError
from apps.core.pagination import CatalogPagination
from apps.core.schema import error_responses

from . import mojang, selectors, services
from .filters import SkinFilter
from .models import Skin
from .serializers import (
    LookupQuerySerializer,
    LookupResultSerializer,
    MySkinSerializer,
    SkinAddResultSerializer,
    SkinAddSerializer,
    SkinCardSerializer,
    SkinDetailSerializer,
)

THROTTLE_SCOPES = {"lookup": "lookup", "create": "uploads"}
# The router regex hides the type of the pk from drf-spectacular
SKIN_ID = OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH)


def detail_response(request: Request, skin: Skin, *, code: int = status.HTTP_200_OK) -> Response:
    context = {"request": request, "my_skin_id": selectors.my_skin_id(request.user)}
    return Response(SkinDetailSerializer(skin, context=context).data, status=code)


@extend_schema_view(
    list=extend_schema(operation_id="skins_list", summary="Catalog of skins from the sources"),
    retrieve=extend_schema(
        operation_id="skins_retrieve",
        parameters=[SKIN_ID],
        responses={200: SkinDetailSerializer, **error_responses(404)},
    ),
    create=extend_schema(
        operation_id="skins_add",
        request=SkinAddSerializer,
        responses={
            202: SkinAddResultSerializer,
            200: SkinAddResultSerializer,
            **error_responses(400, 401, 429),
        },
        description="Add a skin to the catalog: a Java nickname (Mojang) or a MineSkin link or "
        "UUID. 202 — poll GET /jobs/{job_id}; 200 — the skin is already here (`id`).",
    ),
)
class SkinViewSet(
    GuestCachedListMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    pagination_class = CatalogPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = SkinFilter
    http_method_names = ["get", "post", "head", "options"]
    lookup_value_regex = r"\d+"
    throttle_scope: str | None = None

    def get_permissions(self):
        return [IsAuthenticated()] if self.action == "create" else [AllowAny()]

    def get_throttles(self):
        self.throttle_scope = THROTTLE_SCOPES.get(self.action)
        return super().get_throttles()

    def get_queryset(self):
        return selectors.catalog(self.request.user)

    def get_serializer_class(self):
        return SkinCardSerializer if self.action in ("list", "similar") else SkinDetailSerializer

    def get_object(self) -> Skin:
        return selectors.get_skin(pk=self.kwargs["pk"], viewer=self.request.user)

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        return detail_response(request, self.get_object())

    def create(self, request: Request, *args, **kwargs) -> Response:
        data = SkinAddSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        result = services.request_add(user=request.user, **data.validated_data)
        if result.skin_id is not None:
            return Response({"id": result.skin_id, "title": result.title})
        return Response({"job_id": result.job_id}, status=status.HTTP_202_ACCEPTED)

    @extend_schema(
        operation_id="skins_download",
        parameters=[SKIN_ID],
        responses={
            (200, "image/png"): OpenApiResponse(OpenApiTypes.BINARY, description="Skin PNG"),
            **error_responses(404),
        },
        description="The PNG as an attachment; counts the download.",
    )
    @action(detail=True, methods=["get"])
    def download(self, request: Request, pk: str) -> FileResponse:
        skin = self.get_object()
        services.record_download(skin=skin)
        return FileResponse(
            skin.texture.open("rb"),
            as_attachment=True,
            filename=get_valid_filename(f"{skin.title}.png") or "skin.png",
            content_type="image/png",
        )

    @extend_schema(
        operation_id="skins_similar",
        parameters=[SKIN_ID],
        responses={200: SkinCardSerializer(many=True)},
    )
    @action(detail=True, methods=["get"], pagination_class=None)
    def similar(self, request: Request, pk: str) -> Response:
        skin = self.get_object()
        cards = selectors.similar(skin=skin, viewer=request.user)
        return Response(SkinCardSerializer(cards, many=True).data)

    @extend_schema(
        operation_id="skins_lookup",
        parameters=[LookupQuerySerializer],
        responses={200: LookupResultSerializer, **error_responses(400, 404, 503)},
        description="A Java player's skin via Mojang, cached for 10 minutes (2 for unknown).",
    )
    @action(detail=False, methods=["get"], pagination_class=None, filter_backends=[])
    def lookup(self, request: Request) -> Response:
        query = LookupQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        try:
            player = mojang.lookup(query.validated_data["nickname"])
        except mojang.MojangError as error:
            raise DomainError(
                code="mojang_unavailable",
                message="Mojang зараз не відповідає. Спробуй за хвилину.",
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from error
        if player is None:
            raise DomainError(
                code="player_not_found",
                message="Гравця з таким ніком не знайдено.",
                status=status.HTTP_404_NOT_FOUND,
            )
        texture = (
            "data:image/png;base64," + base64.b64encode(player.texture_png).decode()
            if player.texture_png
            else None
        )
        result = {
            "nickname": player.nickname,
            "uuid": player.uuid,
            "model": player.model,
            "texture": texture,
        }
        return Response(LookupResultSerializer(result).data)


class MySkinView(APIView):
    """«Мій скін»: any skin of the catalog, shown in the profile."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="me_skin_set",
        request=MySkinSerializer,
        responses={200: SkinDetailSerializer, **error_responses(400, 401, 404)},
    )
    def put(self, request: Request) -> Response:
        data = MySkinSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        skin = selectors.get_skin(pk=data.validated_data["skin_id"], viewer=request.user)
        services.set_my_skin(user=request.user, skin=skin)
        return detail_response(request, skin)

    @extend_schema(operation_id="me_skin_clear", responses={204: None, **error_responses(401)})
    def delete(self, request: Request) -> Response:
        services.clear_my_skin(user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
