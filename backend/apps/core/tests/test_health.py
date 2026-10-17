import pytest
import redis
from django.db import OperationalError
from django.urls import reverse

from apps.core import health

pytestmark = pytest.mark.django_db


class BrokenConnection:
    def cursor(self):
        raise OperationalError("connection refused")


@pytest.fixture
def redis_up(monkeypatch):
    monkeypatch.setattr(redis.Redis, "ping", lambda self: True)


@pytest.fixture
def redis_down(monkeypatch):
    def ping(self):
        raise redis.ConnectionError("connection refused")

    monkeypatch.setattr(redis.Redis, "ping", ping)


def test_health_ok_when_database_and_redis_available(api_client, redis_up):
    response = api_client.get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok", "redis": "ok"}}


def test_health_503_when_redis_unavailable(api_client, redis_down):
    response = api_client.get(reverse("health"))

    assert response.status_code == 503
    assert response.json() == {"status": "error", "checks": {"database": "ok", "redis": "error"}}


def test_health_503_when_database_unavailable(api_client, redis_up, monkeypatch):
    monkeypatch.setattr(health, "connection", BrokenConnection())

    response = api_client.get(reverse("health"))

    assert response.status_code == 503
    assert response.json() == {"status": "error", "checks": {"database": "error", "redis": "ok"}}


def test_health_is_served_at_documented_path(api_client, redis_up):
    assert reverse("health") == "/api/v1/health"
    assert api_client.get("/api/v1/health").status_code == 200
