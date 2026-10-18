from django.conf import settings
from django.db import transaction
from django.db.models import Model
from django.db.models.signals import post_delete, post_save

from apps.core import kinds


def _on_save(sender: type[Model], instance: Model, **kwargs) -> None:
    if not settings.SEARCH_INDEXING:
        return
    from . import tasks

    kind, pk = kinds.kind_for_model(sender).name, instance.pk
    transaction.on_commit(lambda: tasks.index_object.delay(kind, pk))


def _on_delete(sender: type[Model], instance: Model, **kwargs) -> None:
    if not settings.SEARCH_INDEXING:
        return
    from . import tasks

    kind, pk = kinds.kind_for_model(sender).name, instance.pk
    transaction.on_commit(lambda: tasks.remove_object.delay(kind, pk))


def watch_kind(kind: kinds.Kind) -> None:
    """Per model, like social.signals: other models keep fast bulk deletes."""
    post_save.connect(_on_save, sender=kind.model, dispatch_uid=f"search.save.{kind.name}")
    post_delete.connect(_on_delete, sender=kind.model, dispatch_uid=f"search.delete.{kind.name}")
