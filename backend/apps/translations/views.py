from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import CatalogPagination
from apps.core.schema import error_responses

from . import selectors, services
from .models import Translation
from .serializers import (
    QueueItemSerializer,
    TranslationProposeSerializer,
    TranslationReviewSerializer,
    TranslationSerializer,
    TranslationsQuerySerializer,
)


class IsModerator(BasePermission):
    def has_permission(self, request, view) -> bool:
        return bool(request.user.is_authenticated and request.user.is_moderator)


class TranslationsView(APIView):
    throttle_scope = "translations"

    def get_permissions(self):
        return [AllowAny()] if self.request.method == "GET" else [IsAuthenticated()]

    def get_throttles(self):
        # Reading is free; proposing is limited
        if self.request.method == "GET":
            self.throttle_scope = None
        return super().get_throttles()

    @extend_schema(
        operation_id="translations_list",
        parameters=[TranslationsQuerySerializer],
        responses={200: TranslationSerializer(many=True), **error_responses(400, 404)},
        description="Published translations of the object; the viewer's own pending and "
        "rejected ones; for moderators every pending one.",
    )
    def get(self, request: Request) -> Response:
        query = TranslationsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        kind, target = services.resolve_target(
            kind=query.validated_data["kind"],
            identifier=query.validated_data["id"],
            viewer=request.user,
        )
        rows = selectors.for_target(kind=kind, target=target, viewer=request.user)
        return Response(TranslationSerializer(rows, many=True).data)

    @extend_schema(
        operation_id="translations_propose",
        request=TranslationProposeSerializer,
        responses={201: TranslationSerializer, **error_responses(400, 401, 404, 429)},
        description="Goes to moderators; a second proposal of the same field replaces the "
        "player's pending one.",
    )
    def post(self, request: Request) -> Response:
        data = TranslationProposeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        translation = services.propose(
            user=request.user,
            kind=data.validated_data["kind"],
            identifier=data.validated_data["id"],
            field=data.validated_data["field"],
            text=data.validated_data["text"],
        )
        return Response(TranslationSerializer(translation).data, status=status.HTTP_201_CREATED)


class TranslationReviewView(APIView):
    permission_classes = [IsModerator]

    @extend_schema(
        operation_id="translations_review",
        request=TranslationReviewSerializer,
        responses={200: TranslationSerializer, **error_responses(400, 401, 403, 404)},
        description="Moderators only: approve (shown on the page with a byline) or reject.",
    )
    def post(self, request: Request, pk: int) -> Response:
        data = TranslationReviewSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        translation = services.review(
            translation=get_object_or_404(Translation, pk=pk),
            moderator=request.user,
            approve=data.validated_data["decision"] == "approve",
            reason=data.validated_data.get("reason", ""),
        )
        return Response(TranslationSerializer(translation).data)


class TranslationQueueView(APIView):
    permission_classes = [IsModerator]

    @extend_schema(
        operation_id="translations_queue",
        responses={200: QueueItemSerializer(many=True), **error_responses(401, 403)},
        description="Moderators only: pending translations, oldest first.",
    )
    def get(self, request: Request) -> Response:
        paginator = CatalogPagination()
        page = paginator.paginate_queryset(selectors.queue(), request, view=self)
        return paginator.get_paginated_response(QueueItemSerializer(page, many=True).data)
