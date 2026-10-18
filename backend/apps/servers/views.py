from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.cache import for_guests
from apps.core.pagination import CatalogPagination
from apps.core.schema import error_responses

from . import selectors, services
from . import status as live_status
from .filters import ServerFilter
from .models import Server
from .serializers import (
    BannerUploadSerializer,
    IpCopiesSerializer,
    ServerCardSerializer,
    ServerDetailSerializer,
    ServerWriteSerializer,
    StatsQuerySerializer,
    StatsSerializer,
    VerificationSerializer,
)

WRITE_ACTIONS = {"create", "partial_update", "destroy", "banner", "verify"}
THROTTLE_SCOPES = {"create": "uploads", "banner": "uploads", "copy_ip": "copy_ip"}


@extend_schema_view(
    list=extend_schema(operation_id="servers_list", summary="Catalog of published servers"),
    retrieve=extend_schema(
        operation_id="servers_retrieve",
        responses={200: ServerDetailSerializer, **error_responses(404)},
        description="Published servers for everyone; the owner also sees pending ones.",
    ),
    create=extend_schema(
        operation_id="servers_create",
        request=ServerWriteSerializer,
        responses={201: ServerDetailSerializer, **error_responses(400, 401)},
        description="A new author's first three works wait for moderation (`pending`).",
    ),
    partial_update=extend_schema(
        operation_id="servers_update",
        request=ServerWriteSerializer(partial=True),
        responses={200: ServerDetailSerializer, **error_responses(400, 401, 403, 404)},
        description="Changing host, port or edition resets the verification.",
    ),
    destroy=extend_schema(
        operation_id="servers_delete", responses={204: None, **error_responses(401, 403, 404)}
    ),
)
class ServerViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """No PUT on the server itself: edits are PATCH, PUT is the banner upload."""

    lookup_field = "slug"
    pagination_class = CatalogPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = ServerFilter
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]
    throttle_scope: str | None = None

    def get_permissions(self):
        if self.action in WRITE_ACTIONS and not (
            self.action == "verify" and self.request.method == "GET"
        ):
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_throttles(self):
        self.throttle_scope = THROTTLE_SCOPES.get(self.action)
        return super().get_throttles()

    def get_queryset(self):
        return selectors.catalog(self.request.user)

    def get_serializer_class(self):
        return ServerCardSerializer if self.action == "list" else ServerDetailSerializer

    def get_object(self) -> Server:
        return selectors.get_server(slug=self.kwargs["slug"], viewer=self.request.user)

    def _detail(self, server: Server, *, status_code: int = status.HTTP_200_OK) -> Response:
        server = selectors.get_server(slug=server.slug, viewer=self.request.user)
        context = {"request": self.request, "live": live_status.get_many([server.pk])}
        return Response(ServerDetailSerializer(server, context=context).data, status=status_code)

    def list(self, request: Request, *args, **kwargs) -> Response:
        def build() -> Response:
            page = self.paginate_queryset(self.filter_queryset(self.get_queryset()))
            context = {"request": request, "live": live_status.get_many(s.pk for s in page)}
            return self.get_paginated_response(
                ServerCardSerializer(page, many=True, context=context).data
            )

        # Guests share a page for a minute: the pings themselves come every five
        return for_guests(request, build)

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        return self._detail(self.get_object())

    def create(self, request: Request, *args, **kwargs) -> Response:
        data = ServerWriteSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        server = services.create_server(author=request.user, data=data.validated_data)
        return self._detail(server, status_code=status.HTTP_201_CREATED)

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        server = self.get_object()
        data = ServerWriteSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        services.update_server(server=server, user=request.user, data=data.validated_data)
        return self._detail(server)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        services.delete_server(server=self.get_object(), user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        operation_id="servers_stats",
        parameters=[StatsQuerySerializer],
        responses={200: StatsSerializer, **error_responses(404)},
        description="24h: every 5-minute ping; 7d: hourly averages. Uptime in %.",
    )
    @action(detail=True, methods=["get"])
    def stats(self, request: Request, slug: str) -> Response:
        server = self.get_object()
        query = StatsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        return Response(
            StatsSerializer(
                selectors.stats(server=server, range_name=query.validated_data["range"])
            ).data
        )

    @extend_schema(
        methods=["GET"],
        operation_id="servers_verification",
        responses={200: VerificationSerializer, **error_responses(404)},
        description="Outcome of the latest MOTD check.",
    )
    @extend_schema(
        methods=["POST"],
        operation_id="servers_verify",
        request=None,
        responses={202: VerificationSerializer, **error_responses(401, 403, 404)},
        description="Queues a check of the MOTD for the code; poll GET for the outcome.",
    )
    @action(detail=True, methods=["get", "post"])
    def verify(self, request: Request, slug: str) -> Response:
        server = self.get_object()
        if request.method == "POST":
            state = services.request_verification(server=server, user=request.user)
            return Response({"state": state}, status=status.HTTP_202_ACCEPTED)
        state = "verified" if server.is_verified else live_status.get_verification(server.pk)
        return Response({"state": state or "idle"})

    @extend_schema(
        methods=["PUT"],
        operation_id="servers_banner_upload",
        request={"multipart/form-data": BannerUploadSerializer},
        responses={200: ServerDetailSerializer, **error_responses(400, 401, 403, 404)},
    )
    @extend_schema(
        methods=["DELETE"],
        operation_id="servers_banner_delete",
        responses={200: ServerDetailSerializer, **error_responses(401, 403, 404)},
    )
    @action(detail=True, methods=["put", "delete"], parser_classes=[MultiPartParser])
    def banner(self, request: Request, slug: str) -> Response:
        server = self.get_object()
        if request.method == "DELETE":
            services.remove_banner(server=server, user=request.user)
        else:
            data = BannerUploadSerializer(data=request.data)
            data.is_valid(raise_exception=True)
            services.set_banner(
                server=server, user=request.user, upload=data.validated_data["banner"]
            )
        return self._detail(server)

    @extend_schema(
        operation_id="servers_copy_ip",
        request=None,
        responses={200: IpCopiesSerializer, **error_responses(404, 429)},
        description="Counts «Скопіювати IP»; anyone may call it, rate-limited.",
    )
    @action(detail=True, methods=["post"], url_path="copy-ip")
    def copy_ip(self, request: Request, slug: str) -> Response:
        server = self.get_object()
        services.record_ip_copy(server=server)
        server.refresh_from_db(fields=["ip_copies_count"])
        return Response({"ip_copies_count": server.ip_copies_count})


@extend_schema_view(
    get=extend_schema(operation_id="me_servers_list", description="All my servers, any status.")
)
class MyServersView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ServerDetailSerializer
    pagination_class = CatalogPagination

    def get_queryset(self):
        return selectors.my_servers(self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["live"] = live_status.get_many(
            self.get_queryset().values_list("pk", flat=True)[:60]
        )
        return context
