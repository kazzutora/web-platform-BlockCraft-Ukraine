import logging
import re
from collections.abc import Callable

from django.conf import settings
from django.db.models import Q, QuerySet

from apps.core.game import GameContext
from apps.core.text import transliterate

from . import documents
from .client import MeiliClient, SearchUnavailableError

logger = logging.getLogger(__name__)

GROUP_LIMIT = 5
PAGE_SIZE = 24
BATCH = 1000
#: Order of groups in the results: what players look for most comes first
KIND_ORDER = ["mod", "pack", "skin", "server", "collection"]

ClientFactory = Callable[[], MeiliClient]


def _connect(factory: ClientFactory | None) -> MeiliClient:
    # Looked up at call time, so tests can replace `MeiliClient`
    return (factory or MeiliClient)()


def ensure_index(client: MeiliClient, uid: str | None = None) -> None:
    uid = uid or settings.SEARCH_INDEX
    if client.index_exists(uid):
        return
    client.wait(client.create_index(uid, primary_key="uid"))
    client.wait(client.update_settings(uid, documents.INDEX_SETTINGS))


def index_object(*, kind: str, pk: int, client_factory: ClientFactory | None = None) -> bool:
    """Puts the object into the index, or takes it out when it is no longer public."""
    document = documents.document_for(kind, pk)
    with _connect(client_factory) as client:
        ensure_index(client)
        if document is None:
            client.delete_documents(settings.SEARCH_INDEX, [f"{kind}-{pk}"])
            return False
        client.add_documents(settings.SEARCH_INDEX, [document])
    return True


def remove_object(*, kind: str, pk: int, client_factory: ClientFactory | None = None) -> None:
    with _connect(client_factory) as client:
        client.delete_documents(settings.SEARCH_INDEX, [f"{kind}-{pk}"])


def reindex_all(*, client_factory: ClientFactory | None = None, batch: int = BATCH) -> int:
    """Builds a fresh index next to the live one and swaps them: search never goes empty."""
    uid = settings.SEARCH_INDEX
    fresh = f"{uid}_fresh"
    count = 0
    with _connect(client_factory) as client:
        if client.index_exists(fresh):
            client.wait(client.delete_index(fresh))
        ensure_index(client, fresh)
        for source in documents.SOURCES.values():
            chunk: list[dict] = []
            for obj in source.queryset().iterator(chunk_size=batch):
                chunk.append(source.document(obj))
                if len(chunk) == batch:
                    client.wait(client.add_documents(fresh, chunk))
                    count += len(chunk)
                    chunk = []
            if chunk:
                client.wait(client.add_documents(fresh, chunk))
                count += len(chunk)
        ensure_index(client, uid)
        client.wait(client.swap_indexes(uid, fresh))
        client.wait(client.delete_index(fresh))
    return count


def _group(kind: str, hits: list[dict], total: int, page: int, limit: int) -> dict:
    has_more = page * limit < total
    return {
        "kind": kind,
        "total": total,
        "results": hits,
        "next_page": page + 1 if has_more else None,
    }


def _db_game_filter(queryset: QuerySet, kind: str, game: GameContext | None) -> QuerySet:
    """`game_filter` for the database fallback: the catalogs' own rules."""
    if game is None or not game.is_set or kind not in ("mod", "pack"):
        return queryset
    from apps.mods.selectors import for_loader
    from apps.packs.choices import PackLoader

    if kind == "mod":
        if game.game_version:
            queryset = queryset.filter(game_versions__contains=[game.game_version])
        return queryset.filter(for_loader(game.loader))
    if game.game_version:
        queryset = queryset.filter(game_version=game.game_version)
    if game.loader in PackLoader.values:
        queryset = queryset.filter(loader=game.loader)
    return queryset


def _fallback(
    q: str,
    kind: str | None,
    page: int,
    *,
    twin: str | None = None,
    game: GameContext | None = None,
    only_my_game: bool = False,
) -> list[dict]:
    """Title search in the database while Meilisearch is down: no typos, but no dead end."""
    groups = []
    limit = PAGE_SIZE if kind else GROUP_LIMIT
    for name in [kind] if kind else KIND_ORDER:
        source = documents.SOURCES[name]
        title_field = "name" if name == "server" else "title"
        matches = Q(**{f"{title_field}__icontains": q})
        if twin:
            matches |= Q(**{f"{title_field}__icontains": twin})
        queryset = source.queryset().filter(matches)
        if only_my_game:
            queryset = _db_game_filter(queryset, name, game)
        total = queryset.count()
        objects = queryset.order_by("-score")[(page - 1) * limit : page * limit]
        hits = [source.document(obj) for obj in objects]
        if hits or kind:
            groups.append(_group(name, hits, total, page, limit))
    return groups


_CYRILLIC = re.compile(r"[а-яіїєґ]", re.IGNORECASE)


def latin_twin(q: str) -> str | None:
    """«содіум» → «sodium»: a Cyrillic query also searched in Latin (R8.2)."""
    if not _CYRILLIC.search(q):
        return None
    twin = transliterate(q).lower()
    return twin if twin != q.lower() else None


def game_filter(kind: str, game: GameContext | None) -> str:
    """«Моя гра» as a Meilisearch filter: the same rule as the catalogs (mods.selectors)."""
    if game is None or not game.is_set or kind not in ("mod", "pack"):
        return ""
    parts = []
    if game.game_version:
        parts.append(f"game_versions = {_quoted(game.game_version)}")
    if game.loader:
        if kind == "pack":
            # A vanilla game has no pack loader: packs for any loader (packs.filters)
            if game.loader != "vanilla":
                parts.append(f"loaders = {_quoted(game.loader)}")
        else:
            wanted = "datapack" if game.loader == "vanilla" else game.loader
            parts.append(f'(project_type != "mod" OR loaders = {_quoted(wanted)})')
    return " AND ".join(parts)


def _quoted(value: str) -> str:
    """A string literal of the Meilisearch filter syntax."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def fits(hit: dict, game: GameContext | None) -> bool | None:
    """`fits_my_game` of a hit; None when nothing is chosen or the kind has no game."""
    if game is None or not game.is_set or hit.get("kind") not in ("mod", "pack"):
        return None
    versions, loaders = hit.get("game_versions") or [], hit.get("loaders") or []
    if game.game_version and game.game_version not in versions:
        return False
    if not game.loader:
        return True
    if hit["kind"] == "pack":
        return game.loader == "vanilla" or game.loader in loaders
    if hit.get("project_type") != "mod":
        return True
    return ("datapack" if game.loader == "vanilla" else game.loader) in loaders


def _merge(first: list[dict], second: list[dict], limit: int) -> list[dict]:
    """Hits of the query as typed, then new ones of its Latin twin."""

    def key(hit: dict) -> str:
        return hit.get("uid") or f"{hit.get('kind')}-{hit.get('id')}"

    seen = {key(hit) for hit in first}
    return (first + [hit for hit in second if key(hit) not in seen])[:limit]


def search(
    *,
    q: str,
    kind: str | None = None,
    page: int = 1,
    game: GameContext | None = None,
    only_my_game: bool = False,
    client_factory: ClientFactory | None = None,
) -> list[dict]:
    """Groups by kind (5 hits each), or one full page of a single kind.

    A Cyrillic query is also searched transliterated; `only_my_game` keeps mods and packs
    that fit «Моя гра»; every mod and pack hit says whether it fits.

    With the twin both queries read from the top up to the end of the page and the merged
    list is cut: hits of the twin stay on the pages they fall on, none repeats.
    """
    kinds = [kind] if kind else KIND_ORDER
    limit = PAGE_SIZE if kind else GROUP_LIMIT
    start = (page - 1) * limit
    twin = latin_twin(q)
    texts = [q, twin] if twin else [q]
    queries = []
    for name in kinds:
        conditions = [f'kind = "{name}"']
        if only_my_game and (extra := game_filter(name, game)):
            conditions.append(extra)
        for text in texts:
            queries.append(
                {
                    "indexUid": settings.SEARCH_INDEX,
                    "q": text,
                    "filter": " AND ".join(conditions),
                    # One more with the twin: tells whether the union goes on
                    "limit": start + limit + 1 if twin else limit,
                    "offset": 0 if twin else start,
                }
            )
    try:
        with _connect(client_factory) as client:
            results = client.multi_search(queries)
    except SearchUnavailableError as error:
        logger.warning("Search falls back to the database: %s", error)
        groups = _fallback(q, kind, page, twin=twin, game=game, only_my_game=only_my_game)
    else:
        groups = []
        step = len(texts)
        for index, name in enumerate(kinds):
            own = results[index * step : index * step + step]
            totals = [result.get("estimatedTotalHits", len(result["hits"])) for result in own]
            if twin:
                merged = _merge(own[0]["hits"], own[1]["hits"], start + limit + 1)
                hits = merged[start : start + limit]
                # The union: at least the larger total and at least what was merged
                totals.append(len(merged))
            else:
                hits = own[0]["hits"]
            total = max(totals)
            if hits or kind:
                groups.append(_group(name, hits, total, page, limit))
    for group in groups:
        for hit in group["results"]:
            hit["fits_my_game"] = fits(hit, game)
    return groups
