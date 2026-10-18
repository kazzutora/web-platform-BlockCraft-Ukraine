"""Single error format for the whole API: {"detail": str, "code": str, "fields": {field: [str]}}."""

from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error
from rest_framework.views import exception_handler as drf_exception_handler

INVALID_DETAIL = "Перевір введені дані."


class DomainError(Exception):
    """Business rule violation raised by services; becomes a 400 (or `status`) response."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        fields: dict[str, list[str]] | None = None,
        status: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.fields = fields or {}
        self.status = status


def _flatten(errors: Any, prefix: str = "") -> dict[str, list[str]]:
    """Turns nested serializer errors into {"field": [...], "nested.field": [...]}."""
    if isinstance(errors, dict):
        flat: dict[str, list[str]] = {}
        for key, value in errors.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            flat.update(_flatten(value, name))
        return flat
    if isinstance(errors, list) and errors and all(isinstance(e, dict | list) for e in errors):
        flat = {}
        for index, value in enumerate(errors):
            flat.update(_flatten(value, f"{prefix}.{index}" if prefix else str(index)))
        return flat
    items = errors if isinstance(errors, list) else [errors]
    return {prefix or "non_field_errors": [str(item) for item in items]}


def handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, DomainError):
        return Response(
            {"detail": exc.message, "code": exc.code, "fields": exc.fields}, status=exc.status
        )
    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(as_serializer_error(exc))
    elif isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, exceptions.ValidationError):
        fields = _flatten(exc.detail)
        general = fields.get("non_field_errors")
        response.data = {
            "detail": general[0] if general else INVALID_DETAIL,
            "code": "invalid",
            "fields": fields,
        }
        return response

    if isinstance(exc, exceptions.NotAuthenticated):
        # Session auth has no WWW-Authenticate header, so DRF would answer 403
        response.status_code = status.HTTP_401_UNAUTHORIZED
    detail = exc.detail if isinstance(exc, exceptions.APIException) else str(exc)
    code = exc.get_codes() if isinstance(exc, exceptions.APIException) else "error"
    response.data = {
        "detail": str(detail),
        "code": code if isinstance(code, str) else "error",
        "fields": {},
    }
    return response
