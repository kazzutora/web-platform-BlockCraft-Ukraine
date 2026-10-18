import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import Http404

from apps.core import kinds
from apps.core.exceptions import DomainError
from apps.library.models import Collection
from apps.library.tests.factories import CollectionFactory
from apps.mods.models import Project
from apps.mods.tests.factories import ProjectFactory

pytestmark = pytest.mark.django_db


def test_registered_kinds():
    assert {"mod", "collection"} <= set(kinds.names())
    assert kinds.get_kind("mod").rating == "review"
    assert kinds.get_kind("collection").rating == "like"


def test_mod_is_resolved_by_slug_only_when_published():
    project = ProjectFactory(slug="sodium")
    ProjectFactory(slug="waiting", status=Project.Status.PENDING)

    kind, obj = kinds.resolve("mod", "sodium")
    assert (kind.name, obj) == ("mod", project)
    assert kind.identifier(obj) == "sodium"
    with pytest.raises(Http404):
        kinds.resolve("mod", "waiting")


def test_collection_visibility_depends_on_viewer(user):
    private = CollectionFactory(owner=user, visibility=Collection.Visibility.PRIVATE)
    public = CollectionFactory(visibility=Collection.Visibility.PUBLIC)

    assert kinds.resolve("collection", private.pk, viewer=user)[1] == private
    assert kinds.resolve("collection", str(public.pk), viewer=AnonymousUser())[1] == public
    with pytest.raises(Http404):
        kinds.resolve("collection", private.pk, viewer=AnonymousUser())
    with pytest.raises(Http404):
        kinds.resolve("collection", "not-a-number")


def test_unknown_kind_and_forbidden_action():
    ProjectFactory(slug="sodium")

    with pytest.raises(DomainError) as unknown:
        kinds.resolve("planet", "earth")
    assert unknown.value.code == "unknown_kind"

    with pytest.raises(DomainError) as forbidden:
        kinds.resolve("mod", "sodium", action="like")
    assert forbidden.value.code == "action_not_allowed"
