from rest_framework import serializers
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from apps.core.exceptions import DomainError, handler


class NestedSerializer(serializers.Serializer):
    name = serializers.CharField()


class FormSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=3)
    items = NestedSerializer(many=True)


def run(exc: Exception):
    request = APIRequestFactory().get("/")
    return handler(exc, {"request": request, "view": APIView()})


def test_validation_errors_become_flat_fields():
    serializer = FormSerializer(data={"title": "too long", "items": [{}]})
    serializer.is_valid()

    response = run(serializers.ValidationError(serializer.errors))

    assert response.status_code == 400
    assert response.data["code"] == "invalid"
    assert set(response.data["fields"]) == {"title", "items.0.name"}
    assert response.data["detail"] == "Перевір введені дані."


def test_non_field_error_becomes_detail():
    response = run(serializers.ValidationError("Колекція вже існує."))

    assert response.data["detail"] == "Колекція вже існує."
    assert response.data["fields"] == {"non_field_errors": ["Колекція вже існує."]}


def test_domain_error_keeps_code_message_and_status():
    response = run(DomainError(code="limit", message="Не частіше разу на 30 днів.", status=429))

    assert response.status_code == 429
    assert response.data == {"detail": "Не частіше разу на 30 днів.", "code": "limit", "fields": {}}
