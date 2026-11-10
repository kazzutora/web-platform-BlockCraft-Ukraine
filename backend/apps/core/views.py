from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import jobs
from .health import get_health_report
from .schema import error_responses
from .serializers import HealthSerializer, JobSerializer


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


class JobView(APIView):
    """State of a background job a page waits for; the random id is the access key."""

    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="jobs_retrieve",
        summary="Background job state",
        responses={200: JobSerializer, **error_responses(404)},
        tags=["core"],
    )
    def get(self, request: Request, job_id: str) -> Response:
        job = jobs.get(job_id)
        if job is None:
            raise Http404
        return Response(JobSerializer(job).data)
