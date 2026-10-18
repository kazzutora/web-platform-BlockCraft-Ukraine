from django.shortcuts import redirect
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.exceptions import DomainError
from apps.core.pagination import CatalogPagination
from apps.core.schema import error_responses

from . import selectors, services, tasks
from .filters import ProjectFilter
from .models import Category, Project, ProjectType
from .serializers import (
    CategorySerializer,
    DownloadQuerySerializer,
    NoVersionErrorSerializer,
    ProjectCardSerializer,
    ProjectDetailSerializer,
    SuggestResponseSerializer,
    SuggestSerializer,
    VersionsQuerySerializer,
    VersionsSerializer,
)

LOADER_LABELS = {"fabric": "Fabric", "forge": "Forge", "neoforge": "NeoForge", "quilt": "Quilt"}


@extend_schema_view(
    list=extend_schema(operation_id="mods_list", summary="Catalog of mods, packs and shaders"),
    retrieve=extend_schema(
        operation_id="mods_retrieve",
        responses={200: ProjectDetailSerializer, **error_responses(404)},
    ),
)
class ModViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    lookup_field = "slug"
    pagination_class = CatalogPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProjectFilter
    # Set per action (`suggest`); None means only the default anon throttle applies
    throttle_scope: str | None = None

    def get_queryset(self):
        return selectors.catalog()

    def get_serializer_class(self):
        return ProjectDetailSerializer if self.action == "retrieve" else ProjectCardSerializer

    def get_object(self) -> Project:
        return selectors.get_project(slug=self.kwargs["slug"])

    @extend_schema(
        operation_id="mods_versions",
        parameters=[VersionsQuerySerializer],
        responses={200: VersionsSerializer, **error_responses(404)},
    )
    @action(detail=True, methods=["get"])
    def versions(self, request: Request, slug: str) -> Response:
        project = self.get_object()
        query = VersionsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        game_version = query.validated_data.get("game_version", "")
        loader = query.validated_data.get("loader", "")

        versions = list(
            selectors.versions_for(project=project, game_version=game_version, loader=loader)[:50]
        )
        recommended = versions[0] if game_version and versions else None
        nearest = (
            selectors.nearest_game_versions(
                project=project, game_version=game_version, loader=loader
            )
            if game_version and not versions
            else []
        )
        payload = {
            "game_version": game_version,
            "loader": loader,
            "recommended": recommended,
            "dependencies": selectors.dependencies_of(recommended),
            "nearest_game_versions": nearest,
            "versions": versions,
        }
        return Response(VersionsSerializer(payload).data)

    @extend_schema(
        operation_id="mods_download",
        parameters=[DownloadQuerySerializer],
        responses={
            302: None,
            404: NoVersionErrorSerializer,
        },
        description="Redirects to the file on Modrinth and counts the download.",
    )
    @action(detail=True, methods=["get"])
    def download(self, request: Request, slug: str) -> Response:
        project = self.get_object()
        query = DownloadQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        game_version = query.validated_data.get("game_version", "")
        loader = query.validated_data.get("loader", "")
        version_id = query.validated_data.get("version", "")

        if version_id:
            version = project.versions.filter(modrinth_version_id=version_id).first()
        elif game_version:
            version = selectors.resolve_version(
                project=project, game_version=game_version, loader=loader
            )
        else:
            version = selectors.versions_for(project=project).first()

        if version is None:
            target = " · ".join(
                part
                for part in (
                    game_version,
                    LOADER_LABELS.get(loader, loader)
                    if project.project_type == ProjectType.MOD
                    else "",
                )
                if part
            )
            raise DomainError(
                code="no_version",
                message=f"Для {target or 'цих умов'} немає файлу. Спробуй найближчі версії.",
                status=status.HTTP_404_NOT_FOUND,
                extra={
                    "nearest_game_versions": selectors.nearest_game_versions(
                        project=project, game_version=game_version, loader=loader
                    )
                    if game_version
                    else []
                },
            )
        services.record_download(
            project=project,
            version=version,
            user=request.user,
            game_version=game_version,
            loader=loader,
        )
        return redirect(version.file_url)

    @extend_schema(operation_id="mods_similar", responses={200: ProjectCardSerializer(many=True)})
    @action(detail=True, methods=["get"], pagination_class=None)
    def similar(self, request: Request, slug: str) -> Response:
        project = self.get_object()
        cards = selectors.similar(project=project)
        return Response(ProjectCardSerializer(cards, many=True).data)

    @extend_schema(
        operation_id="mods_suggest",
        request=SuggestSerializer,
        responses={
            202: SuggestResponseSerializer,
            200: SuggestResponseSerializer,
            **error_responses(400, 401),
        },
        description="Queue a Modrinth project for import; it waits for moderation.",
    )
    @action(
        detail=False,
        methods=["post"],
        permission_classes=[IsAuthenticated],
        throttle_scope="uploads",
    )
    def suggest(self, request: Request) -> Response:
        serializer = SuggestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        slug = serializer.validated_data["url"]
        if Project.objects.filter(slug=slug).exists():
            return Response({"slug": slug, "status": "exists"})
        tasks.import_project.delay(slug=slug, suggested_by_id=request.user.pk)
        return Response({"slug": slug, "status": "queued"}, status=status.HTTP_202_ACCEPTED)


@extend_schema_view(
    list=extend_schema(
        operation_id="categories_list",
        parameters=[OpenApiParameter("type", enum=ProjectType.values, description="Project type")],
    )
)
class CategoryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    pagination_class = None

    def get_queryset(self):
        queryset = Category.objects.all()
        project_type = self.request.query_params.get("type")
        if project_type in ProjectType.values:
            queryset = queryset.filter(project_type=project_type)
        return queryset
