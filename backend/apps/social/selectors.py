from django.db.models import (
    BooleanField,
    Exists,
    IntegerField,
    OuterRef,
    Prefetch,
    QuerySet,
    Subquery,
    Value,
)

from apps.core.kinds import Kind, Viewer
from apps.library.models import Favorite

from .models import Comment, Like, Review


def with_viewer_state(queryset: QuerySet, *, viewer: Viewer, kind: Kind) -> QuerySet:
    """Adds is_favorited, is_liked, my_review_stars for the viewer as subqueries (no N+1)."""
    if not viewer.is_authenticated:
        return queryset.annotate(
            is_favorited=Value(False, output_field=BooleanField()),
            is_liked=Value(False, output_field=BooleanField()),
            my_review_stars=Value(None, output_field=IntegerField()),
        )
    target = {"content_type": kind.content_type, "object_id": OuterRef("pk")}
    return queryset.annotate(
        is_favorited=Exists(Favorite.objects.filter(user=viewer, **target)),
        is_liked=Exists(Like.objects.filter(user=viewer, **target)),
        my_review_stars=Subquery(
            Review.objects.filter(user=viewer, **target).values("stars")[:1],
            output_field=IntegerField(),
        ),
    )


def reviews_for(*, kind: Kind, object_id: int, sort: str = "helpful") -> QuerySet[Review]:
    ordering = ["-helpful_count", "-created_at"] if sort == "helpful" else ["-created_at"]
    return (
        Review.objects.filter(
            content_type=kind.content_type, object_id=object_id, status=Review.Status.PUBLISHED
        )
        .select_related("user")
        .order_by(*ordering)
    )


def review_distribution(*, kind: Kind, object_id: int) -> dict[str, int]:
    rows = (
        Review.objects.filter(
            content_type=kind.content_type, object_id=object_id, status=Review.Status.PUBLISHED
        )
        .values_list("stars")
        .order_by()
    )
    distribution = dict.fromkeys(("1", "2", "3", "4", "5"), 0)
    for (stars,) in rows:
        distribution[str(stars)] += 1
    return distribution


def comments_for(*, kind: Kind, object_id: int) -> QuerySet[Comment]:
    """Top-level comments with their replies (one level), authors included."""
    return (
        Comment.objects.published()
        .filter(content_type=kind.content_type, object_id=object_id, parent__isnull=True)
        .select_related("user")
        .prefetch_related(
            Prefetch(
                "replies",
                queryset=Comment.objects.published().select_related("user").order_by("created_at"),
            )
        )
    )
