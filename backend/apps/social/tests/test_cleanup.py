import pytest
from django.db.models.signals import post_delete

from apps.accounts.tests.factories import UserFactory
from apps.library import services as library
from apps.library.models import CollectionItem, Favorite
from apps.library.tests.factories import CollectionFactory
from apps.mods.models import Project, ProjectVersion
from apps.mods.tests.factories import ProjectFactory
from apps.social import services
from apps.social.models import Comment, Like

pytestmark = pytest.mark.django_db


def test_deleting_a_collection_removes_what_points_at_it():
    collection = CollectionFactory()
    fan = UserFactory()
    library.add_favorite(user=fan, kind="collection", identifier=str(collection.pk))
    services.like(user=fan, kind="collection", identifier=str(collection.pk))
    services.add_comment(user=fan, kind="collection", identifier=str(collection.pk), body="Клас")

    collection.delete()

    assert not Favorite.objects.exists()
    assert not Like.objects.exists()
    assert not Comment.objects.exists()


def test_deleting_a_mod_takes_it_out_of_collections():
    owner = UserFactory()
    collection = CollectionFactory(owner=owner)
    gone, kept = ProjectFactory(slug="gone"), ProjectFactory(slug="kept")
    for project in (gone, kept):
        library.add_item(collection=collection, user=owner, kind="mod", identifier=project.slug)

    gone.delete()

    collection.refresh_from_db()
    assert collection.items_count == 1
    assert list(CollectionItem.objects.values_list("object_id", flat=True)) == [kept.pk]


def test_other_models_keep_fast_deletes():
    # A global receiver would make Django load every row before bulk deletes (mods sync)
    assert not post_delete.has_listeners(ProjectVersion)
    assert post_delete.has_listeners(Project)
