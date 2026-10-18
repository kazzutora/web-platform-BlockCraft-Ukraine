import pytest

from apps.skins.tasks import render_preview

from .factories import SkinFactory

pytestmark = pytest.mark.django_db


def test_preview_is_rendered_again_without_leftovers():
    skin = SkinFactory()

    assert render_preview.delay(skin.pk).get() is True
    skin.refresh_from_db()
    first = skin.preview.name
    render_preview.delay(skin.pk).get()
    skin.refresh_from_db()

    assert skin.preview.name != first
    assert not skin.preview.storage.exists(first)


def test_preview_of_a_deleted_skin_is_skipped():
    assert render_preview.delay(10**9).get() is False
