from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.schema import error_responses

from . import services
from .models import Notification
from .serializers import (
    MarkReadSerializer,
    NotificationSerializer,
    NotificationsPageSerializer,
    NotificationsQuerySerializer,
    UnreadSerializer,
)

PAGE_SIZE = 20


class NotificationsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="me_notifications",
        parameters=[NotificationsQuerySerializer],
        responses={200: NotificationsPageSerializer, **error_responses(401)},
    )
    def get(self, request: Request) -> Response:
        query = NotificationsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        page = query.validated_data["page"]
        start = (page - 1) * PAGE_SIZE
        rows = list(Notification.objects.filter(user=request.user)[start : start + PAGE_SIZE + 1])
        data = {
            "unread_count": services.unread_count(request.user),
            "results": NotificationSerializer(rows[:PAGE_SIZE], many=True).data,
            "next_page": page + 1 if len(rows) > PAGE_SIZE else None,
        }
        return Response(NotificationsPageSerializer(data).data)


class UnreadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="me_notifications_unread",
        responses={200: UnreadSerializer, **error_responses(401)},
        description="The bell asks this every 60 seconds.",
    )
    def get(self, request: Request) -> Response:
        return Response({"unread_count": services.unread_count(request.user)})


class MarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="me_notifications_read",
        request=MarkReadSerializer,
        responses={200: UnreadSerializer, **error_responses(400, 401)},
    )
    def post(self, request: Request) -> Response:
        data = MarkReadSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.mark_read(user=request.user, ids=data.validated_data.get("ids"))
        return Response({"unread_count": services.unread_count(request.user)})
