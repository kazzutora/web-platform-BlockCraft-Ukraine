from django.db.models import F, Model
from django.db.models.functions import Greatest


def bump(obj: Model, field: str, delta: int = 1) -> None:
    """Atomic `field += delta` in the database (never below zero); call inside a transaction."""
    # `_meta.model`, not `type(obj)`: request.user is a lazy proxy
    obj._meta.model._base_manager.filter(pk=obj.pk).update(**{field: Greatest(F(field) + delta, 0)})
