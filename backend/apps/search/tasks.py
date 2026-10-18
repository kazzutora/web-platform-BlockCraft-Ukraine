from celery import shared_task

from . import services


@shared_task(
    name="search.index_object", autoretry_for=(Exception,), retry_backoff=True, max_retries=3
)
def index_object(kind: str, pk: int) -> bool:
    """After a save: the object enters, changes in or leaves the index."""
    return services.index_object(kind=kind, pk=pk)


@shared_task(
    name="search.remove_object", autoretry_for=(Exception,), retry_backoff=True, max_retries=3
)
def remove_object(kind: str, pk: int) -> None:
    services.remove_object(kind=kind, pk=pk)


@shared_task(name="search.reindex_all")
def reindex_all() -> int:
    """Daily at 05:00 and after big imports: counters and ratings change without signals."""
    return services.reindex_all()
