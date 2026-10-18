import pytest
from django.core.management import call_command

from apps.accounts.models import User
from apps.home import demo
from apps.library.models import Collection
from apps.mods.models import Project
from apps.mods.tests.factories import ProjectFactory
from apps.servers.models import Server
from apps.skins.models import Skin
from apps.social.models import Comment, Review

pytestmark = pytest.mark.django_db


def test_demo_content_is_complete_and_consistent():
    ProjectFactory.create_batch(12)

    summary = demo.create()

    assert (summary.users, summary.skins, summary.servers) == (20, 20, 8)
    assert Skin.objects.published().filter(preview__gt="").count() == 20
    assert Server.objects.published().count() == 8
    assert Collection.objects.filter(visibility="public").count() == summary.collections == 10
    assert Review.objects.count() == summary.reviews
    assert Comment.objects.count() == summary.comments
    rated = Project.objects.filter(rating_count__gt=0).first()
    mod_reviews = Review.objects.filter(content_type__model="project", object_id=rated.pk)
    assert rated.rating_count == mod_reviews.count()


def test_reset_replaces_the_demo_and_fixes_counters():
    project = ProjectFactory()
    demo.create()
    project.refresh_from_db()
    assert project.favorites_count > 0

    call_command("seed", "--reset")
    demo.remove()

    project.refresh_from_db()
    assert project.favorites_count == 0
    assert not User.objects.filter(email__endswith=f"@{demo.DEMO_DOMAIN}").exists()
