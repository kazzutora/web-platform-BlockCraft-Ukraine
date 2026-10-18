import math
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.library.models import Download, Favorite
from apps.mods.tests.factories import ProjectFactory
from apps.skins.tests.factories import SkinFactory
from apps.social import services
from apps.social.models import Like, Review
from apps.social.tasks import recalc_trends

pytestmark = pytest.mark.django_db


def aged(model, hours, **fields):
    obj = model.objects.create(**fields)
    model.objects.filter(pk=obj.pk).update(created_at=timezone.now() - timedelta(hours=hours))
    return obj


def test_recent_events_weigh_more_and_old_ones_drop_out():
    now = timezone.now()
    fresh, old = SkinFactory(), SkinFactory(trend_score=99)
    ct = services.kinds.get_kind("skin").content_type
    aged(Like, 0, user=UserFactory(), content_type=ct, object_id=fresh.pk)
    aged(Favorite, 48, user=UserFactory(), content_type=ct, object_id=fresh.pk)
    aged(Like, 24 * 20, user=UserFactory(), content_type=ct, object_id=old.pk)

    services.recalc_trends(now=now)

    fresh.refresh_from_db()
    old.refresh_from_db()
    assert fresh.trend_score == pytest.approx(1 + 2 * math.exp(-1), rel=1e-3)
    assert old.trend_score == 0


def test_mods_count_downloads_and_reviews():
    project = ProjectFactory()
    ct = services.kinds.get_kind("mod").content_type
    aged(Download, 0, user=UserFactory(), project=project)
    aged(Review, 0, user=UserFactory(), content_type=ct, object_id=project.pk, stars=5)

    recalc_trends.delay().get()

    project.refresh_from_db()
    assert project.trend_score == pytest.approx(0.5 + 3, rel=1e-3)
