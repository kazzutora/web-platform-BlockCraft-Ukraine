import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def auth_client(user) -> APIClient:
    client = APIClient()
    client.force_login(user)
    return client


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    # Uploaded files never land in the real media directory
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture(autouse=True)
def _clear_cache():
    # Rate limits (allauth, DRF throttles) live in the cache and must not leak between tests
    cache.clear()
    yield
    cache.clear()
