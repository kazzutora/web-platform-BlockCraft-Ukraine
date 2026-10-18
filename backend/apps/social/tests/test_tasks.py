import pytest
from django.conf import settings

from apps.mods.tests.factories import ProjectFactory
from apps.social.tasks import recalc_scores

pytestmark = pytest.mark.django_db


def test_recalc_scores_task_is_scheduled_hourly():
    entry = next(
        item
        for item in settings.CELERY_BEAT_SCHEDULE.values()
        if item["task"] == "social.recalc_scores"
    )
    assert entry["schedule"].minute == {15}


def test_recalc_scores_task_reports_updated_objects():
    ProjectFactory(slug="lithium")

    result = recalc_scores.delay().get()

    assert result["mod"] == 0
    assert "collection" in result
