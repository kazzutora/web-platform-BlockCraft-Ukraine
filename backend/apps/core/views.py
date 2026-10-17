from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .health import get_health_report
from .serializers import HealthSerializer


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="health",
        summary="Service health",
        description="Checks that the database and Redis are reachable.",
        responses={200: HealthSerializer, 503: HealthSerializer},
        tags=["core"],
    )
    def get(self, request: Request) -> Response:
        report = get_health_report()
        http_status = (
            status.HTTP_200_OK if report["status"] == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(HealthSerializer(report).data, status=http_status)
