import pytest

pytestmark = pytest.mark.django_db


def test_openapi_schema_describes_health(api_client):
    response = api_client.get("/api/schema/", HTTP_ACCEPT="application/json")

    assert response.status_code == 200
    schema = response.json()
    health = schema["paths"]["/api/v1/health"]["get"]
    assert set(health["responses"]) == {"200", "503"}


def test_swagger_ui_is_available(api_client):
    response = api_client.get("/api/docs/")

    assert response.status_code == 200
    assert b"swagger" in response.content.lower()
