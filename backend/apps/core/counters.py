from django.db.models import F, Model
from django.db.models.functions import Greatest


def bump(obj: Model, field: str, delta: int = 1) -> None:
    """Atomic `field += delta` in the database (never below zero); call inside a transaction."""
    type(obj)._base_manager.filter(pk=obj.pk).update(**{field: Greatest(F(field) + delta, 0)})
