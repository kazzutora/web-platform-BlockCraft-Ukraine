from django.db.models import Model
from django.db.models.signals import post_delete

from apps.core import kinds

from . import services


def _forget_deleted(sender: type[Model], instance: Model, **kwargs) -> None:
    services.forget_target(kind=kinds.kind_for_model(sender), object_id=instance.pk)


def watch_deletions(kind: kinds.Kind) -> None:
    """Per model, not a global receiver: a global one would disable Django's fast deletes."""
    post_delete.connect(
        _forget_deleted, sender=kind.model, dispatch_uid=f"social.forget.{kind.name}"
    )
