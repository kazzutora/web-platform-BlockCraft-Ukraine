from django.contrib.auth.models import AnonymousUser
from django.db.models import Q, QuerySet
from django.http import Http404

from apps.accounts.models import User
from apps.core.kinds import Viewer, get_kind
from apps.social.selectors import with_viewer_state

from .models import Skin

SIMILAR_LIMIT = 8


def _with_state(queryset: QuerySet[Skin], viewer: Viewer | None) -> QuerySet[Skin]:
    queryset = queryset.select_related("author")
    return with_viewer_state(queryset, viewer=viewer or AnonymousUser(), kind=get_kind("skin"))


def catalog(viewer: Viewer | None = None) -> QuerySet[Skin]:
    """Published skins with the viewer's favorite/like state annotated."""
    return _with_state(Skin.objects.published(), viewer)


def get_skin(*, pk: int, viewer: Viewer | None = None) -> Skin:
    """Published skins for everyone; the author and moderators also see the rest."""
    viewer = viewer or AnonymousUser()
    queryset = Skin.objects.all()
    if not viewer.is_authenticated:
        queryset = queryset.filter(status=Skin.Status.PUBLISHED)
    elif not viewer.is_moderator:
        queryset = queryset.filter(Q(status=Skin.Status.PUBLISHED) | Q(author=viewer))
    try:
        return _with_state(queryset, viewer).get(pk=pk)
    except Skin.DoesNotExist as error:
        raise Http404 from error


def similar(*, skin: Skin, viewer: Viewer | None = None) -> list[Skin]:
    """Same colour first, then most shared styles, then popularity."""
    queryset = (
        catalog(viewer)
        .exclude(pk=skin.pk)
        .filter(Q(color_bucket=skin.color_bucket) | Q(style_tags__overlap=skin.style_tags))
    )
    return list(queryset.order_by("-likes_count", "-downloads_count")[:SIMILAR_LIMIT])


def my_skins(user: User) -> QuerySet[Skin]:
    """All of the author's skins, any status."""
    return _with_state(Skin.objects.filter(author=user), user).order_by("-created_at")


def current_skin_of(user: User) -> Skin | None:
    return Skin.objects.filter(author=user, is_current=True, status=Skin.Status.PUBLISHED).first()
