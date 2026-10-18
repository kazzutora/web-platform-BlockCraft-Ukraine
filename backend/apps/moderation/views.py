from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.schema import error_responses

from . import services
from .serializers import ReportCreatedSerializer, ReportCreateSerializer


class ReportsView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "reports"

    @extend_schema(
        operation_id="reports_create",
        request=ReportCreateSerializer,
        responses={201: ReportCreatedSerializer, **error_responses(400, 401, 404, 429)},
        description="A report on any reportable kind or a comment; five open ones hide the object.",
    )
    def post(self, request: Request) -> Response:
        data = ReportCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        report = services.report(
            reporter=request.user,
            kind=data.validated_data["kind"],
            identifier=data.validated_data["id"],
            reason=data.validated_data["reason"],
            comment=data.validated_data.get("comment", ""),
        )
        return Response({"id": report.pk, "status": report.status}, status=status.HTTP_201_CREATED)
