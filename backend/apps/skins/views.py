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
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import DomainError
from apps.core.pagination import CatalogPagination
from apps.core.schema import error_responses

from . import mojang, selectors, services
from .filters import SkinFilter
from .models import Skin
from .serializers import (
    CurrentSkinSerializer,
    LookupQuerySerializer,
    LookupResultSerializer,
    SkinCardSerializer,
    SkinDetailSerializer,
    SkinUpdateSerializer,
    SkinUploadSerializer,
)

WRITE_ACTIONS = {"create", "partial_update", "destroy"}
THROTTLE_SCOPES = {"create": "uploads", "lookup": "lookup"}
# The router regex hides the type of the pk from drf-spectacular
SKIN_ID = OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH)


@extend_schema_view(
    list=extend_schema(operation_id="skins_list", summary="Catalog of published skins"),
    retrieve=extend_schema(
        operation_id="skins_retrieve",
        parameters=[SKIN_ID],
        responses={200: SkinDetailSerializer, **error_responses(404)},
        description="Published skins for everyone; the author also sees pending and rejected.",
    ),
    create=extend_schema(
        operation_id="skins_create",
        request={"multipart/form-data": SkinUploadSerializer},
        responses={201: SkinDetailSerializer, **error_responses(400, 401)},
        description="A new author's first three skins wait for moderation (`pending`).",
    ),
    partial_update=extend_schema(
        operation_id="skins_update",
        parameters=[SKIN_ID],
        request=SkinUpdateSerializer,
        responses={200: SkinDetailSerializer, **error_responses(400, 401, 403, 404)},
    ),
    destroy=extend_schema(
        operation_id="skins_delete",
        parameters=[SKIN_ID],
        responses={204: None, **error_responses(401, 403, 404)},
    ),
)
class SkinViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    pagination_class = CatalogPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = SkinFilter
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    lookup_value_regex = r"\d+"
    throttle_scope: str | None = None

    def get_permissions(self):
        return [IsAuthenticated()] if self.action in WRITE_ACTIONS else [AllowAny()]

    def get_throttles(self):
        self.throttle_scope = THROTTLE_SCOPES.get(self.action)
        return super().get_throttles()

    def get_parsers(self):
        if getattr(self, "action", None) == "create":
            return [MultiPartParser(), FormParser()]
        return super().get_parsers()

    def get_queryset(self):
        return selectors.catalog(self.request.user)

    def get_serializer_class(self):
        return SkinCardSerializer if self.action in ("list", "similar") else SkinDetailSerializer

    def get_object(self) -> Skin:
        return selectors.get_skin(pk=self.kwargs["pk"], viewer=self.request.user)

    def _detail(self, skin: Skin, *, status_code: int = status.HTTP_200_OK) -> Response:
        skin = selectors.get_skin(pk=skin.pk, viewer=self.request.user)
        serializer = SkinDetailSerializer(skin, context={"request": self.request})
        return Response(serializer.data, status=status_code)

    def create(self, request: Request, *args, **kwargs) -> Response:
        data = SkinUploadSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        skin = services.upload_skin(
            author=request.user,
            upload=data.validated_data["file"],
            title=data.validated_data["title"],
            style_tags=data.validated_data["style_tags"],
            model=data.validated_data["model"],
        )
        return self._detail(skin, status_code=status.HTTP_201_CREATED)

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        skin = self.get_object()
        data = SkinUpdateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.update_skin(skin=skin, user=request.user, **data.validated_data)
        return self._detail(skin)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        services.delete_skin(skin=self.get_object(), user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

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
            skin.file.open("rb"),
            as_attachment=True,
            filename=get_valid_filename(f"{skin.title}.png"),
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


@extend_schema_view(
    get=extend_schema(operation_id="me_skins_list", description="All my skins, any status.")
)
class MySkinsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SkinDetailSerializer
    pagination_class = CatalogPagination

    def get_queryset(self):
        return selectors.my_skins(self.request.user)


class CurrentSkinView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="me_skin_set",
        request=CurrentSkinSerializer,
        responses={200: SkinDetailSerializer, **error_responses(400, 401, 403, 404)},
        description="The skin shown in my profile.",
    )
    def put(self, request: Request) -> Response:
        data = CurrentSkinSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        skin = selectors.get_skin(pk=data.validated_data["skin_id"], viewer=request.user)
        services.set_current(user=request.user, skin=skin)
        skin = selectors.get_skin(pk=skin.pk, viewer=request.user)
        return Response(SkinDetailSerializer(skin, context={"request": request}).data)

    @extend_schema(operation_id="me_skin_clear", responses={204: None, **error_responses(401)})
    def delete(self, request: Request) -> Response:
        services.clear_current(user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
