import pytest
from django.core.management import CommandError, call_command

from apps.accounts.models import User
from apps.home import demo
from apps.library.models import Collection
from apps.mods.models import Project
from apps.mods.tests.factories import ProjectFactory, VersionFactory
from apps.packs.models import Pack
from apps.social.models import Review

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("game_versions")]


def test_demo_content_is_complete_and_consistent():
    ProjectFactory.create_batch(12)

    summary = demo.create()

    assert summary.users == 20
    assert Collection.objects.filter(visibility="public").count() == summary.collections == 10
    assert Review.objects.count() == summary.reviews
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


def test_seed_needs_synced_mods_and_invents_nothing():
    with pytest.raises(CommandError, match="make sync s=modrinth"):
        call_command("seed", "--reset")

    assert not Project.objects.exists()
    assert not User.objects.exists()


def test_demo_packs_are_built_from_catalog_files():
    for _ in range(6):
        VersionFactory(project=ProjectFactory(), game_versions=["1.21.1"], loaders=["fabric"])

    summary = demo.create()

    assert summary.packs == 4
    pack = Pack.objects.published().first()
    assert (pack.game_version, pack.loader) == ("1.21.1", "fabric")
    assert pack.items.count() >= 4
    assert pack.rating_count == 2
    demo.remove()
    assert not Pack.objects.exists()


def test_demo_translations_wait_for_a_moderator_and_only_for_the_text_they_translate():
    from apps.translations.models import Translation

    english, _ = demo.TRANSLATIONS["sodium"]
    ProjectFactory(slug="sodium", summary=english)
    ProjectFactory(slug="lithium", summary="A newer summary on Modrinth")

    summary = demo.create()

    rows = Translation.objects.all()
    assert summary.translations == 1
    assert [(row.target.slug, row.status, row.field) for row in rows] == [
        ("sodium", "pending", "summary")
    ]
