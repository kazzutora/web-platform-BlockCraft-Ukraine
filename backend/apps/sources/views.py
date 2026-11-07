from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from . import selectors
from .serializers import MetaSerializer, SourceSerializer


class MetaView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(operation_id="meta_retrieve", responses=MetaSerializer)
    def get(self, request: Request) -> Response:
        return Response(MetaSerializer(selectors.meta()).data)


class SourcesView(APIView):
    """«Звідки дані»: every source, its terms and when we last synced it."""

    permission_classes = [AllowAny]

    @extend_schema(operation_id="sources_list", responses=SourceSerializer(many=True))
    def get(self, request: Request) -> Response:
        return Response(SourceSerializer(selectors.sources_overview(), many=True).data)
