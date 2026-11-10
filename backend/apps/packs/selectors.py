from django.contrib.auth.models import AnonymousUser
from django.db.models import Case, IntegerField, Prefetch, Q, QuerySet, Value, When
from django.http import Http404

from apps.accounts.models import User
from apps.core.kinds import Viewer, get_kind
from apps.social.selectors import with_viewer_state

from .models import LoaderRelease, Pack, PackItem, Reason, Visibility

PREVIEW_ICONS = 8


def listed() -> QuerySet[Pack]:
    """What anyone may find: published and «усім» (Modrinth modpacks always are)."""
    return Pack.objects.published().filter(visibility=Visibility.PUBLIC)


def _with_state(queryset: QuerySet[Pack], viewer: Viewer | None) -> QuerySet[Pack]:
    queryset = queryset.select_related("author")
    return with_viewer_state(queryset, viewer=viewer or AnonymousUser(), kind=get_kind("pack"))


def _picked_first() -> Case:
    return Case(
        When(reason=Reason.REQUESTED, then=Value(0)), default=Value(1), output_field=IntegerField()
    )


def with_preview(queryset: QuerySet[Pack]) -> QuerySet[Pack]:
    """Icons for cards: projects the author picked first, dependencies after."""
    return queryset.prefetch_related(
        Prefetch(
            "items",
            queryset=PackItem.objects.select_related("project")
            .annotate(picked=_picked_first())
            .order_by("picked", "position", "pk")[:PREVIEW_ICONS],
            to_attr="preview_items",
        )
    )


def catalog(viewer: Viewer | None = None) -> QuerySet[Pack]:
    """Listed packs with the viewer's favorite/review state annotated."""
    return with_preview(_with_state(listed(), viewer))


def get_pack(*, slug: str, viewer: Viewer | None = None, share_token: str = "") -> Pack:
    """Listed packs for everyone; «за посиланням» with its token; the author and moderators
    also see drafts and private ones. Everything else is 404, not 403: it does not exist."""
    viewer = viewer or AnonymousUser()
    visible = Q(status=Pack.Status.PUBLISHED, visibility=Visibility.PUBLIC)
    if share_token:
        visible |= Q(
            status=Pack.Status.PUBLISHED, visibility=Visibility.LINK, share_token=share_token
        )
    if viewer.is_authenticated:
        visible |= Q(author=viewer)
        if viewer.is_moderator:
            visible = Q()
    queryset = (
        _with_state(Pack.objects.filter(visible), viewer)
        .select_related("forked_from")
        .prefetch_related(
            Prefetch(
                "items",
                queryset=PackItem.objects.select_related("project", "version"),
                to_attr="all_items",
            ),
            "external_files",
        )
    )
    try:
        return queryset.get(slug=slug)
    except Pack.DoesNotExist as error:
        raise Http404 from error


def my_packs(user: User) -> QuerySet[Pack]:
    return with_preview(_with_state(Pack.objects.filter(author=user), user)).order_by("-updated_at")


def loader_version(pack: Pack) -> str:
    """The author's pinned build, else the latest stable one we know for the game version."""
    if pack.loader_version:
        return pack.loader_version
    release = LoaderRelease.objects.filter(loader=pack.loader, game_version=pack.game_version)
    return release.values_list("version", flat=True).first() or ""


def titles(slugs: set[str]) -> dict[str, str]:
    """Slug → title for the retarget preview (hidden projects too: they may be in a pack)."""
    from apps.mods.models import Project

    return dict(Project.objects.filter(slug__in=slugs).values_list("slug", "title"))
