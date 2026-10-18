"""OpenAPI helpers shared by all apps."""

from rest_framework import serializers


class ApiErrorSerializer(serializers.Serializer):
    """Shape of every error response (see core.exceptions.handler)."""

    detail = serializers.CharField()
    code = serializers.CharField()
    fields = serializers.DictField(child=serializers.ListField(child=serializers.CharField()))


def error_responses(*status_codes: int) -> dict[int, type[ApiErrorSerializer]]:
    """`responses={200: X, **error_responses(400, 401)}` in extend_schema."""
    return dict.fromkeys(status_codes, ApiErrorSerializer)
