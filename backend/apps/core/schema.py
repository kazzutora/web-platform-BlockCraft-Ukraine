"""OpenAPI helpers shared by all apps."""

from functools import cache

from rest_framework import serializers


class ApiErrorSerializer(serializers.Serializer):
    """Shape of every error response (see core.exceptions.handler)."""

    detail = serializers.CharField()
    code = serializers.CharField()
    fields = serializers.DictField(child=serializers.ListField(child=serializers.CharField()))


def error_responses(*status_codes: int) -> dict[int, type[ApiErrorSerializer]]:
    """`responses={200: X, **error_responses(400, 401)}` in extend_schema."""
    return dict.fromkeys(status_codes, ApiErrorSerializer)


@cache
def paginated(serializer_class: type[serializers.Serializer]) -> type[serializers.Serializer]:
    """Schema of a CatalogPagination page for views that paginate by hand."""
    name = serializer_class.__name__.removesuffix("Serializer")
    return type(
        f"Paginated{name}ListSerializer",
        (serializers.Serializer,),
        {
            "count": serializers.IntegerField(),
            "next": serializers.URLField(allow_null=True),
            "previous": serializers.URLField(allow_null=True),
            "results": serializer_class(many=True),
        },
    )
