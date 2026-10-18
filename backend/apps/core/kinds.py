"""Registry of content kinds that can be saved, rated, commented on and reported.

Every app registers its kinds in AppConfig.ready(); generic relations (favorites, likes,
reviews, comments, reports) store `content_type` + `object_id` and talk to the outside world
in pairs `{kind, id}`, where `id` is a slug or a number depending on the kind.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from django.apps import apps
from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model, QuerySet
from django.http import Http404

from .exceptions import DomainError

Action = Literal["favorite", "like", "review", "comment", "collect", "report"]
Viewer = Any  # User or AnonymousUser


@dataclass(frozen=True)
class Kind:
    name: str
    model_label: str
    #: "slug" or "pk": what `{kind, id}` carries for this kind
    lookup_field: str
    #: How players rate it: 1–5 stars with a review, or a like
    rating: Literal["review", "like"]
    actions: frozenset[str]
    #: Attribute with the owner (pins comments, applies `who_can_comment`); None — nobody
    owner_field: str | None = None
    #: Objects a viewer may see; defaults to `published()` or all objects
    visible: Callable[[Viewer], QuerySet] | None = field(default=None, compare=False)

    @property
    def model(self) -> type[Model]:
        return apps.get_model(self.model_label)

    @property
    def content_type(self) -> ContentType:
        return ContentType.objects.get_for_model(self.model)

    def queryset_for(self, viewer: Viewer) -> QuerySet:
        if self.visible is not None:
            return self.visible(viewer)
        manager = self.model.objects
        return manager.published() if hasattr(manager, "published") else manager.all()

    def identifier(self, obj: Model) -> str:
        return str(getattr(obj, self.lookup_field))

    def owner_of(self, obj: Model) -> Any:
        return getattr(obj, self.owner_field) if self.owner_field else None

    def allows(self, action: Action) -> bool:
        return action in self.actions


_registry: dict[str, Kind] = {}
_listeners: list[Callable[[Kind], None]] = []


def register(kind: Kind) -> None:
    _registry[kind.name] = kind
    for listener in _listeners:
        listener(kind)


def on_register(listener: Callable[[Kind], None]) -> None:
    """Calls `listener` for every kind, registered before or after (apps load in any order)."""
    _listeners.append(listener)
    for kind in _registry.values():
        listener(kind)


def all_kinds() -> list[Kind]:
    return list(_registry.values())


def names() -> list[str]:
    return list(_registry)


def get_kind(name: str) -> Kind:
    try:
        return _registry[name]
    except KeyError as error:
        raise DomainError(
            code="unknown_kind",
            message="Невідомий тип контенту.",
            fields={"kind": ["Невідомий тип контенту."]},
        ) from error


def kind_for_model(model: type[Model]) -> Kind:
    label = model._meta.label
    for kind in _registry.values():
        if kind.model_label == label:
            return kind
    raise LookupError(f"{label} is not a registered kind")


def kind_for_content_type(content_type_id: int) -> Kind:
    model = ContentType.objects.get_for_id(content_type_id).model_class()
    return kind_for_model(model)


def resolve(
    kind_name: str,
    identifier: str | int,
    *,
    viewer: Viewer | None = None,
    action: Action | None = None,
) -> tuple[Kind, Model]:
    """The object behind `{kind, id}` if the viewer may see it (and the kind allows `action`)."""
    kind = get_kind(kind_name)
    if action and not kind.allows(action):
        raise DomainError(
            code="action_not_allowed",
            message="Для цього типу контенту дія недоступна.",
        )
    lookup = {kind.lookup_field: identifier}
    if kind.lookup_field == "pk" and not str(identifier).isdigit():
        raise Http404
    try:
        obj = kind.queryset_for(viewer or AnonymousUser()).get(**lookup)
    except kind.model.DoesNotExist as error:
        raise Http404 from error
    return kind, obj
