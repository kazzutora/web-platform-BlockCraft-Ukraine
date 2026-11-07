from django.http import HttpResponse, HttpResponseRedirect
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
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.cache import GuestCachedListMixin
from apps.core.pagination import CatalogPagination
from apps.core.schema import error_responses

from . import selectors, services
from .filters import PackFilter
from .models import Pack
from .serializers import (
    CoverUploadSerializer,
    MyPackSerializer,
    PackCardSerializer,
    PackDetailSerializer,
    PackItemAddSerializer,
    PackItemUpdateSerializer,
    PackWriteSerializer,
)

WRITE_ACTIONS = {"create", "partial_update", "destroy", "cover", "items", "item", "publish", "fork"}
THROTTLE_SCOPES = {
    "create": "uploads",
    "fork": "uploads",
    "cover": "uploads",
    "items": "pack_edits",
    "item": "pack_edits",
}
PROJECT_SLUG = OpenApiParameter(
    "project_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Catalog project slug."
)


@extend_schema_view(
    list=extend_schema(operation_id="packs_list", summary="Catalog of published packs"),
    retrieve=extend_schema(
        operation_id="packs_retrieve",
        responses={200: PackDetailSerializer, **error_responses(404)},
        description="Published packs for everyone; the author also sees drafts.",
    ),
    create=extend_schema(
        operation_id="packs_create",
        request=PackWriteSerializer,
        responses={201: PackDetailSerializer, **error_responses(400, 401, 403)},
        description="A draft: add mods with `items`, then `publish`.",
    ),
    partial_update=extend_schema(
        operation_id="packs_update",
        request=PackWriteSerializer(partial=True),
        responses={200: PackDetailSerializer, **error_responses(400, 401, 403, 404)},
        description="Changing the game version or loader picks every file again.",
    ),
    destroy=extend_schema(
        operation_id="packs_delete", responses={204: None, **error_responses(401, 403, 404)}
    ),
)
class PackViewSet(
    GuestCachedListMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """No PUT on the pack itself: edits are PATCH, PUT is the cover upload."""

    lookup_field = "slug"
    pagination_class = CatalogPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = PackFilter
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]
    throttle_scope: str | None = None

    def get_permissions(self):
        return [IsAuthenticated()] if self.action in WRITE_ACTIONS else [AllowAny()]

    def get_throttles(self):
        self.throttle_scope = THROTTLE_SCOPES.get(self.action)
        return super().get_throttles()

    def get_queryset(self):
        return selectors.catalog(self.request.user)

    def get_serializer_class(self):
        return PackCardSerializer if self.action == "list" else PackDetailSerializer

    def get_object(self) -> Pack:
        return selectors.get_pack(slug=self.kwargs["slug"], viewer=self.request.user)

    def _detail(self, pack: Pack, *, status_code: int = status.HTTP_200_OK) -> Response:
        pack = selectors.get_pack(slug=pack.slug, viewer=self.request.user)
        return Response(
            PackDetailSerializer(pack, context={"request": self.request}).data, status=status_code
        )

    def create(self, request: Request, *args, **kwargs) -> Response:
        data = PackWriteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        pack = services.create_pack(author=request.user, data=data.validated_data)
        return self._detail(pack, status_code=status.HTTP_201_CREATED)

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        pack = self.get_object()
        data = PackWriteSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        services.update_pack(pack=pack, user=request.user, data=data.validated_data)
        return self._detail(pack)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        services.delete_pack(pack=self.get_object(), user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        operation_id="packs_items_add",
        request=PackItemAddSerializer,
        responses={201: PackDetailSerializer, **error_responses(400, 401, 403, 404)},
        description="Adds the file for the pack's version and loader and its required "
        "dependencies (`added_as_dependency`). Dependencies missing from the catalog are "
        "brought in from Modrinth in the background.",
    )
    @action(detail=True, methods=["post"])
    def items(self, request: Request, slug: str) -> Response:
        pack = self.get_object()
        data = PackItemAddSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.add_item(pack=pack, user=request.user, project_slug=data.validated_data["project"])
        return self._detail(pack, status_code=status.HTTP_201_CREATED)

    @extend_schema(
        methods=["PATCH"],
        operation_id="packs_item_update",
        parameters=[PROJECT_SLUG],
        request=PackItemUpdateSerializer,
        responses={200: PackDetailSerializer, **error_responses(400, 401, 403, 404)},
    )
    @extend_schema(
        methods=["DELETE"],
        operation_id="packs_item_remove",
        parameters=[PROJECT_SLUG],
        responses={200: PackDetailSerializer, **error_responses(401, 403, 404)},
        description="Dependencies nothing else needs leave with it.",
    )
    @action(detail=True, methods=["patch", "delete"], url_path=r"items/(?P<project_slug>[-\w]+)")
    def item(self, request: Request, slug: str, project_slug: str) -> Response:
        pack = self.get_object()
        if request.method == "DELETE":
            services.remove_item(pack=pack, user=request.user, project_slug=project_slug)
        else:
            data = PackItemUpdateSerializer(data=request.data)
            data.is_valid(raise_exception=True)
            services.update_item(
                pack=pack,
                user=request.user,
                project_slug=project_slug,
                is_required=data.validated_data["is_required"],
            )
        return self._detail(pack)

    @extend_schema(
        operation_id="packs_publish",
        request=None,
        responses={200: PackDetailSerializer, **error_responses(400, 401, 403, 404)},
        description="A new author's first three works wait for moderation (`pending`).",
    )
    @action(detail=True, methods=["post"])
    def publish(self, request: Request, slug: str) -> Response:
        pack = self.get_object()
        services.publish_pack(pack=pack, user=request.user)
        return self._detail(pack)

    @extend_schema(
        operation_id="packs_fork",
        request=None,
        responses={201: PackDetailSerializer, **error_responses(401, 403, 404)},
        description="A draft copy owned by the caller.",
    )
    @action(detail=True, methods=["post"])
    def fork(self, request: Request, slug: str) -> Response:
        copy = services.fork_pack(pack=self.get_object(), user=request.user)
        return self._detail(copy, status_code=status.HTTP_201_CREATED)

    @extend_schema(
        operation_id="packs_export",
        responses={
            (200, "application/x-modrinth-modpack+zip"): OpenApiTypes.BINARY,
            302: OpenApiResponse(description="Official packs: the original file on Modrinth."),
            **error_responses(404, 409),
        },
        description="modrinth.index.json in a zip; the files themselves stay on Modrinth.",
    )
    @action(detail=True, methods=["get"], url_path=r"export\.mrpack")
    def export(self, request: Request, slug: str) -> HttpResponse:
        pack = self.get_object()
        if pack.is_official and pack.source_file_url:
            services.record_download(pack=pack)
            return HttpResponseRedirect(pack.source_file_url)
        response = HttpResponse(
            services.export_mrpack(pack=pack), content_type="application/x-modrinth-modpack+zip"
        )
        response["Content-Disposition"] = f'attachment; filename="{pack.slug}.mrpack"'
        return response

    @extend_schema(
        methods=["PUT"],
        operation_id="packs_cover_upload",
        request={"multipart/form-data": CoverUploadSerializer},
        responses={200: PackDetailSerializer, **error_responses(400, 401, 403, 404)},
    )
    @extend_schema(
        methods=["DELETE"],
        operation_id="packs_cover_delete",
        responses={200: PackDetailSerializer, **error_responses(401, 403, 404)},
    )
    @action(detail=True, methods=["put", "delete"], parser_classes=[MultiPartParser])
    def cover(self, request: Request, slug: str) -> Response:
        pack = self.get_object()
        if request.method == "DELETE":
            services.remove_cover(pack=pack, user=request.user)
        else:
            data = CoverUploadSerializer(data=request.data)
            data.is_valid(raise_exception=True)
            services.set_cover(pack=pack, user=request.user, upload=data.validated_data["cover"])
        return self._detail(pack)


@extend_schema_view(
    get=extend_schema(operation_id="me_packs_list", description="All my packs, drafts included.")
)
class MyPacksView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MyPackSerializer
    pagination_class = CatalogPagination

    def get_queryset(self):
        return selectors.my_packs(self.request.user)
