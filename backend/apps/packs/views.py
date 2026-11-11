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
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.compat.serializers import ResolutionSerializer
from apps.core.cache import GuestCachedListMixin
from apps.core.game import game_context
from apps.core.pagination import CatalogPagination
from apps.core.schema import error_responses

from . import selectors, services
from .filters import PackFilter
from .models import Env, Pack
from .serializers import (
    ForkSerializer,
    MyPackSerializer,
    PackCardSerializer,
    PackDetailSerializer,
    PackFileLinkSerializer,
    PackImportSerializer,
    PackItemAddSerializer,
    PackItemUpdateSerializer,
    PackWriteSerializer,
    PublishSerializer,
    RetargetSerializer,
    TargetQuerySerializer,
)

WRITE_ACTIONS = {
    "create",
    "import_draft",
    "partial_update",
    "destroy",
    "items",
    "item",
    "publish",
    "fork",
}
THROTTLE_SCOPES = {
    "create": "uploads",
    "import_draft": "uploads",
    "fork": "uploads",
    "items": "pack_edits",
    "item": "pack_edits",
    "retarget": "compat",
}
PROJECT_SLUG = OpenApiParameter(
    "project_slug", OpenApiTypes.STR, OpenApiParameter.PATH, description="Catalog project slug."
)
SHARE_TOKEN = OpenApiParameter(
    "share_token",
    OpenApiTypes.STR,
    OpenApiParameter.QUERY,
    required=False,
    description="Opens a pack published «за посиланням».",
)
#: Where each type goes when installed by hand
FOLDERS = {"mod": "mods", "resourcepack": "resourcepacks", "shader": "shaderpacks"}


@extend_schema_view(
    list=extend_schema(operation_id="packs_list", summary="Catalog of listed packs"),
    retrieve=extend_schema(
        operation_id="packs_retrieve",
        parameters=[SHARE_TOKEN],
        responses={200: PackDetailSerializer, **error_responses(404)},
        description="Listed packs for everyone, «за посиланням» with its token; the author "
        "also sees drafts and private ones.",
    ),
    create=extend_schema(
        operation_id="packs_create",
        request=PackWriteSerializer,
        responses={201: PackDetailSerializer, **error_responses(400, 401, 403)},
        description="A draft: add projects with `items`, then `publish`.",
    ),
    partial_update=extend_schema(
        operation_id="packs_update",
        request=PackWriteSerializer(partial=True),
        responses={200: PackDetailSerializer, **error_responses(400, 401, 403, 404)},
        description="Changing the game version or loader resolves the whole set again.",
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
    lookup_field = "slug"
    pagination_class = CatalogPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = PackFilter
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    throttle_scope: str | None = None

    def get_permissions(self):
        return [IsAuthenticated()] if self.action in WRITE_ACTIONS else [AllowAny()]

    def get_throttles(self):
        self.throttle_scope = THROTTLE_SCOPES.get(self.action)
        return super().get_throttles()

    def get_queryset(self):
        return selectors.catalog(self.request.user)

    def get_serializer_context(self) -> dict:
        return {**super().get_serializer_context(), "game": game_context(self.request)}

    def guest_cache_vary(self, request: Request) -> str:
        game = game_context(request)
        return f"{game.game_version}:{game.loader}"

    def get_serializer_class(self):
        return PackCardSerializer if self.action == "list" else PackDetailSerializer

    def get_object(self) -> Pack:
        return selectors.get_pack(
            slug=self.kwargs["slug"],
            viewer=self.request.user,
            share_token=self.request.query_params.get("share_token", ""),
        )

    def _detail(self, pack: Pack, *, status_code: int = status.HTTP_200_OK) -> Response:
        pack = selectors.get_pack(
            slug=pack.slug, viewer=self.request.user, share_token=pack.share_token
        )
        return Response(
            PackDetailSerializer(pack, context=self.get_serializer_context()).data,
            status=status_code,
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
        operation_id="packs_import",
        request=PackImportSerializer,
        responses={201: PackDetailSerializer, **error_responses(400, 401)},
        description="«Зберегти як збірку» on /import: a private draft from hashes or an index.",
    )
    @action(detail=False, methods=["post"], url_path="import")
    def import_draft(self, request: Request) -> Response:
        data = PackImportSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        pack = services.import_draft(author=request.user, data=data.validated_data)
        return self._detail(pack, status_code=status.HTTP_201_CREATED)

    @extend_schema(
        operation_id="packs_items_add",
        request=PackItemAddSerializer,
        responses={201: PackDetailSerializer, **error_responses(400, 401, 403, 404)},
        description="Adds a project; the whole set is resolved again, so its dependencies "
        "and shader engine come with it (`reason`, `required_by`). Dependencies missing from "
        "the catalog are imported in the background (`compat.status = incomplete`).",
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
        responses={200: PackDetailSerializer, **error_responses(400, 401, 403, 404)},
        description="Only projects the author picked; dependencies leave with what needs them.",
    )
    @action(detail=True, methods=["patch", "delete"], url_path=r"items/(?P<project_slug>[-\w.]+)")
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
                optional=data.validated_data["optional"],
            )
        return self._detail(pack)

    @extend_schema(
        operation_id="packs_check",
        parameters=[SHARE_TOKEN],
        responses={200: ResolutionSerializer, **error_responses(404)},
        description="The compatibility report of the pack (kept until the set changes).",
    )
    @action(detail=True, methods=["get"])
    def check(self, request: Request, slug: str) -> Response:
        return Response(services.check(self.get_object()))

    @extend_schema(
        operation_id="packs_retarget",
        parameters=[TargetQuerySerializer, SHARE_TOKEN],
        responses={200: RetargetSerializer, **error_responses(400, 404)},
        description="What a copy for another game would keep, change, lose and gain.",
    )
    @action(detail=True, methods=["get"])
    def retarget(self, request: Request, slug: str) -> Response:
        pack = self.get_object()
        query = TargetQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        target = query.validated_data
        diff = services.retarget_preview(
            pack=pack, game_version=target["game_version"], loader=target["loader"]
        )
        slugs = {*diff.kept, *diff.dropped, *diff.added, *(slug for slug, _, _ in diff.changed)}
        titles = selectors.titles(slugs)
        return Response(
            RetargetSerializer(
                {
                    "target": target,
                    "kept": diff.kept,
                    "changed": [
                        {"project": slug, "old_version": old, "new_version": new}
                        for slug, old, new in diff.changed
                    ],
                    "dropped": diff.dropped,
                    "added": diff.added,
                    "titles": titles,
                }
            ).data
        )

    @extend_schema(
        operation_id="packs_publish",
        request=PublishSerializer,
        responses={200: PackDetailSerializer, **error_responses(400, 401, 403, 404, 409)},
        description="«Усім» or «за посиланням»; a pack with compatibility errors is refused "
        "with `pack_has_errors`.",
    )
    @action(detail=True, methods=["post"])
    def publish(self, request: Request, slug: str) -> Response:
        pack = self.get_object()
        data = PublishSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.publish_pack(
            pack=pack, user=request.user, visibility=data.validated_data["visibility"]
        )
        return self._detail(pack)

    @extend_schema(
        operation_id="packs_fork",
        parameters=[SHARE_TOKEN],
        request=ForkSerializer,
        responses={201: PackDetailSerializer, **error_responses(400, 401, 403, 404)},
        description="A draft copy owned by the caller, for the same game or another one.",
    )
    @action(detail=True, methods=["post"])
    def fork(self, request: Request, slug: str) -> Response:
        data = ForkSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        copy = services.fork_pack(pack=self.get_object(), user=request.user, **data.validated_data)
        return self._detail(copy, status_code=status.HTTP_201_CREATED)

    @extend_schema(
        operation_id="packs_files",
        parameters=[SHARE_TOKEN],
        responses={200: PackFileLinkSerializer(many=True), **error_responses(404)},
        description="Direct links for installing by hand; datapacks go into a world.",
    )
    @action(detail=True, methods=["get"], pagination_class=None)
    def files(self, request: Request, slug: str) -> Response:
        pack = self.get_object()
        rows = [
            {
                "project": item.project,
                "file_name": item.version.file_name,
                "url": item.version.file_url,
                "size": item.version.file_size,
                "folder": FOLDERS.get(item.project.project_type, "datapacks"),
                "optional": item.env_client == Env.OPTIONAL,
            }
            for item in pack.items.select_related("project", "version").order_by("position")
            if item.version is not None
        ]
        return Response(PackFileLinkSerializer(rows, many=True).data)

    @extend_schema(
        operation_id="packs_export",
        parameters=[SHARE_TOKEN],
        responses={
            (200, "application/x-modrinth-modpack+zip"): OpenApiTypes.BINARY,
            302: OpenApiResponse(description="Modrinth modpacks: the original file there."),
            **error_responses(404, 409),
        },
        description="modrinth.index.json in a zip; the files themselves stay on Modrinth.",
    )
    @action(detail=True, methods=["get"], url_path=r"export\.mrpack")
    def export(self, request: Request, slug: str) -> HttpResponse:
        pack = self.get_object()
        if pack.is_modrinth and pack.source_file_url:
            services.record_download(pack=pack, user=request.user)
            return HttpResponseRedirect(pack.source_file_url)
        response = HttpResponse(
            services.export_mrpack(pack=pack, user=request.user),
            content_type="application/x-modrinth-modpack+zip",
        )
        response["Content-Disposition"] = f'attachment; filename="{pack.slug}.mrpack"'
        return response


@extend_schema_view(
    get=extend_schema(operation_id="me_packs_list", description="All my packs, drafts included.")
)
class MyPacksView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MyPackSerializer
    pagination_class = CatalogPagination

    def get_queryset(self):
        return selectors.my_packs(self.request.user)
