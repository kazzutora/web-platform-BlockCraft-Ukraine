from django.contrib.auth.models import AnonymousUser
from django.db.models import QuerySet
from django.http import Http404

from apps.accounts.models import User, UserSettings
from apps.core.kinds import Viewer, get_kind
from apps.social.selectors import with_viewer_state

from .models import Skin

SIMILAR_LIMIT = 8


def _with_state(queryset: QuerySet[Skin], viewer: Viewer | None) -> QuerySet[Skin]:
    return with_viewer_state(queryset, viewer=viewer or AnonymousUser(), kind=get_kind("skin"))


def catalog(viewer: Viewer | None = None) -> QuerySet[Skin]:
    """Skins not hidden by a moderator, with the viewer's saved state annotated."""
    return _with_state(Skin.objects.visible(), viewer)


def get_skin(*, pk: int, viewer: Viewer | None = None) -> Skin:
    try:
        return catalog(viewer).select_related("added_by").get(pk=pk)
    except Skin.DoesNotExist as error:
        raise Http404 from error


def similar(*, skin: Skin, viewer: Viewer | None = None) -> list[Skin]:
    """Same colour and model first, then the same colour; the most saved on top."""
    queryset = catalog(viewer).exclude(pk=skin.pk).filter(color_bucket=skin.color_bucket)
    same_model = list(
        queryset.filter(model=skin.model).order_by("-favorites_count", "-source_views")[
            :SIMILAR_LIMIT
        ]
    )
    if len(same_model) >= SIMILAR_LIMIT:
        return same_model
    rest = queryset.exclude(pk__in=[item.pk for item in same_model]).order_by("-favorites_count")
    return same_model + list(rest[: SIMILAR_LIMIT - len(same_model)])


def my_skin(user: User) -> Skin | None:
    """«Мій скін», unless a moderator hid it since."""
    settings = UserSettings.objects.filter(user=user).select_related("skin").first()
    skin = settings.skin if settings else None
    return skin if skin is not None and not skin.is_hidden else None


def my_skin_id(viewer: Viewer | None) -> int | None:
    if viewer is None or not viewer.is_authenticated:
        return None
    return UserSettings.objects.filter(user=viewer).values_list("skin_id", flat=True).first()
