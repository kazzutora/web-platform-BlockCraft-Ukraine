from dataclasses import dataclass

from django.contrib.auth.models import AnonymousUser
from django.db.models import Count, Prefetch, Q, QuerySet
from django.http import Http404

from apps.accounts.models import User
from apps.core.kinds import Viewer, get_kind
from apps.mods.models import Project
from apps.social.selectors import with_viewer_state

from .models import LoaderRelease, Pack, PackItem

PREVIEW_ICONS = 8

COPY = {
    "no_version": "Немає файлу для {game_version} · {loader} — прибери мод або зміни версію гри.",
    "missing": "Потрібен «{title}», але його немає в зборці.",
    "missing_unknown": "Потрібна залежність, якої поки немає в нашому каталозі.",
    "conflict": "Несумісний із «{title}».",
}


def _with_state(queryset: QuerySet[Pack], viewer: Viewer | None) -> QuerySet[Pack]:
    queryset = queryset.select_related("author").annotate(mods_count=Count("items"))
    return with_viewer_state(queryset, viewer=viewer or AnonymousUser(), kind=get_kind("pack"))


def with_preview(queryset: QuerySet[Pack]) -> QuerySet[Pack]:
    """Icons for cards: mods the author picked first, dependencies after."""
    return queryset.prefetch_related(
        Prefetch(
            "items",
            queryset=PackItem.objects.select_related("project").order_by(
                "added_as_dependency", "position", "pk"
            )[:PREVIEW_ICONS],
            to_attr="preview_items",
        )
    )


def catalog(viewer: Viewer | None = None) -> QuerySet[Pack]:
    """Published packs with the viewer's favorite/review state annotated."""
    return with_preview(_with_state(Pack.objects.published(), viewer))


def get_pack(*, slug: str, viewer: Viewer | None = None) -> Pack:
    """Published packs for everyone; the author and moderators also see drafts and the rest."""
    viewer = viewer or AnonymousUser()
    queryset = Pack.objects.all()
    if not viewer.is_authenticated:
        queryset = queryset.filter(status=Pack.Status.PUBLISHED)
    elif not viewer.is_moderator:
        queryset = queryset.filter(Q(status=Pack.Status.PUBLISHED) | Q(author=viewer))
    queryset = (
        _with_state(queryset, viewer)
        .select_related("forked_from")
        .prefetch_related(
            Prefetch(
                "items",
                queryset=PackItem.objects.select_related("project", "version"),
                to_attr="all_items",
            )
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


@dataclass
class Issue:
    type: str
    project: Project
    message: str
    other: Project | None = None
    #: Modrinth id of a dependency we do not have in the catalog
    other_modrinth_id: str = ""


def inspect(pack: Pack, items: list[PackItem] | None = None) -> list[Issue]:
    """What stops the pack from starting: files missing, dependencies missing, conflicts."""
    if items is None:
        items = list(pack.items.select_related("project", "version"))
    present = {item.project.external_id: item.project for item in items}
    issues: list[Issue] = []
    missing: list[tuple[PackItem, str]] = []
    conflicts: set[frozenset[str]] = set()
    for item in items:
        if item.version is None:
            message = COPY["no_version"].format(
                game_version=pack.game_version, loader=pack.get_loader_display()
            )
            issues.append(Issue(type="no_version", project=item.project, message=message))
            continue
        for dependency in item.version.dependencies:
            project_id = dependency.get("project_id")
            kind = dependency.get("dependency_type")
            if not project_id or project_id == item.project.external_id:
                continue
            if kind == "required" and project_id not in present:
                missing.append((item, project_id))
            elif kind == "incompatible" and project_id in present:
                pair = frozenset({item.project.external_id, project_id})
                if pair in conflicts:
                    continue
                conflicts.add(pair)
                other = present[project_id]
                issues.append(
                    Issue(
                        type="conflict",
                        project=item.project,
                        other=other,
                        message=COPY["conflict"].format(title=other.title),
                    )
                )
    known = {
        project.external_id: project
        for project in Project.objects.visible().filter(
            external_id__in={project_id for _, project_id in missing}
        )
    }
    for item, project_id in missing:
        other = known.get(project_id)
        issues.append(
            Issue(
                type="missing_dependency",
                project=item.project,
                other=other,
                other_modrinth_id="" if other else project_id,
                message=COPY["missing"].format(title=other.title)
                if other
                else COPY["missing_unknown"],
            )
        )
    return issues


def missing_dependency_ids(pack: Pack) -> set[str]:
    """Required dependencies of the pack's files that our catalog does not have yet."""
    return {
        issue.other_modrinth_id
        for issue in inspect(pack)
        if issue.type == "missing_dependency" and issue.other_modrinth_id
    }
