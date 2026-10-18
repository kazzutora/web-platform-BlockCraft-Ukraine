import logging
from collections.abc import Callable

from django.conf import settings

from . import documents
from .client import MeiliClient, SearchUnavailableError

logger = logging.getLogger(__name__)

GROUP_LIMIT = 5
PAGE_SIZE = 24
BATCH = 1000
#: Order of groups in the results: what players look for most comes first
KIND_ORDER = ["mod", "skin", "server", "collection"]

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


def _fallback(q: str, kind: str | None, page: int) -> list[dict]:
    """Title search in the database while Meilisearch is down: no typos, but no dead end."""
    groups = []
    limit = PAGE_SIZE if kind else GROUP_LIMIT
    for name in [kind] if kind else KIND_ORDER:
        source = documents.SOURCES[name]
        title_field = "name" if name == "server" else "title"
        queryset = source.queryset().filter(**{f"{title_field}__icontains": q})
        total = queryset.count()
        objects = queryset.order_by("-score")[(page - 1) * limit : page * limit]
        hits = [source.document(obj) for obj in objects]
        if hits or kind:
            groups.append(_group(name, hits, total, page, limit))
    return groups


def search(
    *, q: str, kind: str | None = None, page: int = 1, client_factory: ClientFactory | None = None
) -> list[dict]:
    """Groups by kind (5 hits each), or one full page of a single kind."""
    kinds = [kind] if kind else KIND_ORDER
    limit = PAGE_SIZE if kind else GROUP_LIMIT
    queries = [
        {
            "indexUid": settings.SEARCH_INDEX,
            "q": q,
            "filter": f'kind = "{name}"',
            "limit": limit,
            "offset": (page - 1) * limit,
        }
        for name in kinds
    ]
    try:
        with _connect(client_factory) as client:
            results = client.multi_search(queries)
    except SearchUnavailableError as error:
        logger.warning("Search falls back to the database: %s", error)
        return _fallback(q, kind, page)
    return [
        _group(
            name, result["hits"], result.get("estimatedTotalHits", len(result["hits"])), page, limit
        )
        for name, result in zip(kinds, results, strict=True)
        if result["hits"] or kind
    ]
