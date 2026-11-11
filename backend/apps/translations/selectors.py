from django.db.models import Model, Q, QuerySet

from apps.core import kinds
from apps.library.activity import target_prefetch

from .models import Translation


def for_target(*, kind: kinds.Kind, target: Model, viewer) -> QuerySet[Translation]:
    """What a page shows: the published translations, the viewer's own pending ones, and for
    moderators every pending one (they decide right on the page)."""
    queryset = Translation.objects.filter(
        content_type=kind.content_type, object_id=target.pk
    ).select_related("author")
    shown = Q(status=Translation.Status.PUBLISHED)
    if viewer.is_authenticated and viewer.is_moderator:
        shown |= Q(status=Translation.Status.PENDING)
    elif viewer.is_authenticated:
        shown |= Q(
            author=viewer, status__in=[Translation.Status.PENDING, Translation.Status.REJECTED]
        )
    return queryset.filter(shown).order_by("field", "-created_at")


def queue() -> QuerySet[Translation]:
    """Pending translations for moderators, oldest first."""
    return (
        Translation.objects.filter(status=Translation.Status.PENDING)
        .select_related("author", "content_type")
        .prefetch_related(target_prefetch())
        .order_by("created_at")
    )
