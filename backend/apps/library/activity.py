"""«Взяв» and «Поділився» of a player (/me, /u/[nickname]; tech.md 10.5, R7.4)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.contrib.contenttypes.prefetch import GenericPrefetch
from django.db.models import Model

from apps.accounts.models import User
from apps.core import kinds

from .models import Collection, Download

#: Each kind of «Поділився» reads at most this many rows: the list is a recent summary
SHARED_LIMIT = 200


@dataclass
class Item:
    type: str
    kind: str | None
    id: str
    title: str
    image: str | None
    created_at: datetime
    status: str | None = None
    action: str | None = None
    stars: int | None = None
    text: str | None = None
    game_version: str = ""
    loader: str = ""


def _image(target: Model) -> str | None:
    from .serializers import thumbnail_of

    return thumbnail_of(target)


def _title(target: Model) -> str:
    return getattr(target, "title", None) or getattr(target, "name", "") or ""


def _about(target: Model | None) -> tuple[str | None, str, str, str | None]:
    """kind, identifier, title, image of a generic target (gone → empty)."""
    if target is None:
        return None, "", "", None
    kind = kinds.kind_for_model(target._meta.model)
    return kind.name, kind.identifier(target), _title(target), _image(target)


def took(user: User):
    """What the player took, newest first, with targets in a fixed number of queries."""
    return (
        Download.objects.filter(user=user, content_type__isnull=False)
        .select_related("content_type")
        .prefetch_related(target_prefetch())
        .order_by("-created_at")
    )


def target_prefetch() -> GenericPrefetch:
    """Targets of generic rows (downloads, reviews, translations) in one query per kind."""
    from apps.mods.models import Project
    from apps.packs.models import Pack
    from apps.servers.models import Server
    from apps.skins.models import Skin

    return GenericPrefetch(
        "target",
        [
            Project.objects.all(),
            Pack.objects.all(),
            Server.objects.all(),
            Skin.objects.all(),
            Collection.objects.all(),
        ],
    )


def took_items(rows) -> list[Item]:
    items = []
    for row in rows:
        kind, identifier, title, image = _about(row.target)
        if kind is None:
            continue
        items.append(
            Item(
                type="took",
                kind=kind,
                id=identifier,
                title=title,
                image=image,
                created_at=row.created_at,
                action=row.action,
                game_version=row.game_version,
                loader=row.loader,
            )
        )
    return items


def shared(user: User, *, public: bool) -> tuple[list[Item], dict[str, int]]:
    """Everything the player gave: packs, collections, reviews, translations, servers, added
    skins — newest first, and how many of each. `public` — only what anyone may see."""
    from apps.packs.models import Origin, Pack, Visibility
    from apps.servers.models import Server
    from apps.skins.models import Skin
    from apps.social.models import Review
    from apps.translations.models import Translation

    packs = Pack.objects.filter(author=user, origin=Origin.COMMUNITY)
    collections = Collection.objects.filter(owner=user)
    reviews = Review.objects.filter(user=user)
    translations = Translation.objects.filter(author=user)
    servers = Server.objects.filter(owner=user, is_verified=True)
    skins = Skin.objects.filter(added_by=user)
    if public:
        packs = packs.filter(status=Pack.Status.PUBLISHED, visibility=Visibility.PUBLIC)
        collections = collections.filter(visibility=Collection.Visibility.PUBLIC, items_count__gt=0)
        reviews = reviews.filter(status=Review.Status.PUBLISHED)
        translations = translations.filter(status=Translation.Status.PUBLISHED)
        servers = servers.filter(is_hidden=False)
        skins = skins.filter(is_hidden=False)
    counts = {
        "packs": packs.count(),
        "collections": collections.count(),
        "reviews": reviews.count(),
        "translations": translations.count(),
        "servers": servers.count(),
        "skins": skins.count(),
    }
    items: list[Item] = []
    for pack in packs.prefetch_related("items__project").order_by("-created_at")[:SHARED_LIMIT]:
        items.append(_own("pack", pack, pack.slug, pack.created_at, status=pack.status))
    for collection in collections.order_by("-created_at")[:SHARED_LIMIT]:
        items.append(
            _own(
                "collection",
                collection,
                str(collection.pk),
                collection.created_at,
                status=collection.visibility,
            )
        )
    for server in servers.order_by("-created_at")[:SHARED_LIMIT]:
        items.append(_own("server", server, server.slug, server.created_at))
    for skin in skins.order_by("-created_at")[:SHARED_LIMIT]:
        items.append(_own("skin", skin, str(skin.pk), skin.created_at))
    review_rows = list(
        reviews.select_related("content_type")
        .prefetch_related(target_prefetch())
        .order_by("-created_at")[:SHARED_LIMIT]
    )
    translation_rows = list(
        translations.select_related("content_type")
        .prefetch_related(target_prefetch())
        .order_by("-created_at")[:SHARED_LIMIT]
    )
    shown = _anyone_sees([*review_rows, *translation_rows]) if public else None
    for review in review_rows:
        if shown is not None and (review.content_type_id, review.object_id) not in shown:
            continue
        kind, identifier, title, image = _about(review.target)
        if kind is not None:
            items.append(
                Item(
                    "review",
                    kind,
                    identifier,
                    title,
                    image,
                    review.created_at,
                    status=review.status,
                    stars=review.stars,
                    text=review.text,
                )
            )
    for translation in translation_rows:
        key = (translation.content_type_id, translation.object_id)
        if shown is not None and key not in shown:
            continue
        kind, identifier, title, image = _about(translation.target)
        if kind is not None:
            items.append(
                Item(
                    "translation",
                    kind,
                    identifier,
                    title,
                    image,
                    translation.created_at,
                    status=translation.status,
                    text=translation.get_field_display(),
                )
            )
    items.sort(key=lambda item: item.created_at, reverse=True)
    return items, counts


def _anyone_sees(rows) -> set[tuple[int, int]]:
    """(content type, id) of the targets a guest may open: a review of a pack its author
    later made private, or of a mod a moderator hid, must not show it on a profile."""
    from django.contrib.auth.models import AnonymousUser

    wanted: dict[int, set[int]] = {}
    for row in rows:
        wanted.setdefault(row.content_type_id, set()).add(row.object_id)
    shown: set[tuple[int, int]] = set()
    for content_type_id, ids in wanted.items():
        kind = kinds.kind_for_content_type(content_type_id)
        visible = kind.queryset_for(AnonymousUser()).filter(pk__in=ids).values_list("pk", flat=True)
        shown.update((content_type_id, pk) for pk in visible)
    return shown


def _own(kind: str, target: Model, identifier: str, created_at: datetime, **extra: Any) -> Item:
    return Item(
        type=kind,
        kind=kind,
        id=identifier,
        title=_title(target),
        image=_image(target),
        created_at=created_at,
        **extra,
    )
