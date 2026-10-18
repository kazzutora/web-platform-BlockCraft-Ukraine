from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.schema import error_responses

from . import services
from .serializers import SearchQuerySerializer, SearchResponseSerializer


class SearchView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="search",
        parameters=[SearchQuerySerializer],
        responses={200: SearchResponseSerializer, **error_responses(400)},
        description=(
            "Typo-tolerant search over mods, skins, servers and public collections: groups of 5, "
            "or with `kind` one page of 24."
        ),
    )
    def get(self, request: Request) -> Response:
        query = SearchQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        q = query.validated_data["q"]
        groups = services.search(
            q=q, kind=query.validated_data.get("kind"), page=query.validated_data["page"]
        )
        return Response(SearchResponseSerializer({"q": q, "groups": groups}).data)
