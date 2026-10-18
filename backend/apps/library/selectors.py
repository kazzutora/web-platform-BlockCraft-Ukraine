from django.db.models import Exists, OuterRef, Prefetch, Q, QuerySet, Subquery
from django.http import Http404

from apps.core.kinds import Kind, Viewer

from .models import Collection, CollectionItem, Favorite

PREVIEW_ITEMS = 4


def _with_preview(queryset: QuerySet[Collection]) -> QuerySet[Collection]:
    """First items of every collection with their targets, in a fixed number of queries."""
    return queryset.select_related("owner").prefetch_related(
        Prefetch(
            "items",
            queryset=CollectionItem.objects.order_by("position", "created_at")[:PREVIEW_ITEMS],
            to_attr="preview_items",
        ),
        "preview_items__target",
    )


def listed_collections(viewer: Viewer) -> QuerySet[Collection]:
    """What a viewer can find and interact with: public ones plus their own and shared ones."""
    if not viewer.is_authenticated:
        return Collection.objects.filter(visibility=Collection.Visibility.PUBLIC)
    return Collection.objects.filter(
        Q(visibility=Collection.Visibility.PUBLIC) | Q(owner=viewer) | Q(editors=viewer)
    ).distinct()


def can_edit(viewer: Viewer, collection: Collection) -> bool:
    if not viewer.is_authenticated:
        return False
    return collection.owner_id == viewer.pk or collection.editors.filter(pk=viewer.pk).exists()


def get_collection(*, pk: int, viewer: Viewer, share_token: str = "") -> Collection:
    """Private: owner and editors; by link: also anyone with the token; public: everyone.

    Hidden collections answer 404 so their existence does not leak.
    """
    try:
        collection = _with_preview(Collection.objects.all()).get(pk=pk)
    except Collection.DoesNotExist as error:
        raise Http404 from error
    if collection.visibility == Collection.Visibility.PUBLIC or can_edit(viewer, collection):
        return collection
    if (
        collection.visibility == Collection.Visibility.LINK
        and share_token
        and share_token == collection.share_token
    ):
        return collection
    raise Http404


def items_of(collection: Collection) -> QuerySet[CollectionItem]:
    return collection.items.select_related("content_type").prefetch_related("target")


def public_collections(*, owner_nickname: str = "") -> QuerySet[Collection]:
    queryset = Collection.objects.filter(visibility=Collection.Visibility.PUBLIC, items_count__gt=0)
    if owner_nickname:
        queryset = queryset.filter(
            owner__nickname__iexact=owner_nickname, owner__settings__collections_visible=True
        )
    return _with_preview(queryset).order_by("-likes_count", "-updated_at")


def my_collections(
    *, user: Viewer, kind: Kind | None = None, object_id: int | None = None
) -> QuerySet[Collection]:
    """Collections the user can add to; with a target, each knows whether it already holds it."""
    queryset = _with_preview(
        Collection.objects.filter(Q(owner=user) | Q(editors=user)).distinct()
    ).order_by("-updated_at")
    if kind is not None and object_id is not None:
        held = CollectionItem.objects.filter(
            collection=OuterRef("pk"), content_type=kind.content_type, object_id=object_id
        )
        queryset = queryset.annotate(contains=Exists(held), item_id=Subquery(held.values("pk")[:1]))
    return queryset


def favorites_of(
    *, user: Viewer, kind: Kind, object_ids: QuerySet | None = None
) -> QuerySet[Favorite]:
    queryset = Favorite.objects.filter(user=user, content_type=kind.content_type)
    if object_ids is not None:
        queryset = queryset.filter(object_id__in=object_ids)
    return queryset.order_by("-created_at")
