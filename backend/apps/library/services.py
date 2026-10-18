from django.db import IntegrityError, transaction
from django.db.models import Max
from django.db.models.functions import Lower

from apps.accounts.models import User
from apps.core import kinds
from apps.core.counters import bump
from apps.core.exceptions import DomainError
from apps.moderation import words

from .models import Collection, CollectionItem, Favorite

COPY_SUFFIX = " (копія)"


# Favorites


@transaction.atomic
def add_favorite(*, user: User, kind: str, identifier: str) -> tuple[kinds.Kind, object]:
    kind_obj, target = kinds.resolve(kind, identifier, viewer=user, action="favorite")
    _, created = Favorite.objects.get_or_create(
        user=user, content_type=kind_obj.content_type, object_id=target.pk
    )
    if created:
        bump(target, "favorites_count", 1)
    return kind_obj, target


@transaction.atomic
def remove_favorite(*, user: User, kind: str, identifier: str) -> tuple[kinds.Kind, object]:
    kind_obj, target = kinds.resolve(kind, identifier, viewer=user, action="favorite")
    deleted, _ = Favorite.objects.filter(
        user=user, content_type=kind_obj.content_type, object_id=target.pk
    ).delete()
    if deleted:
        bump(target, "favorites_count", -1)
    return kind_obj, target


# Collections


def _set_editors(collection: Collection, nicknames: list[str]) -> None:
    wanted = {nickname.lower() for nickname in nicknames}
    editors = list(
        User.objects.annotate(nickname_lower=Lower("nickname"))
        .filter(nickname_lower__in=wanted, is_active=True)
        .exclude(pk=collection.owner_id)
    )
    found = {editor.nickname.lower() for editor in editors}
    missing = [nickname for nickname in nicknames if nickname.lower() not in found]
    if missing:
        message = f"Не знайшли гравців: {', '.join(missing)}."
        raise DomainError(code="unknown_editors", message=message, fields={"editors": [message]})
    collection.editors.set(editors)


@transaction.atomic
def create_collection(
    *,
    owner: User,
    title: str,
    description: str = "",
    visibility: str = Collection.Visibility.PRIVATE,
) -> Collection:
    words.check(title=title, description=description)
    return Collection.objects.create(
        owner=owner, title=title, description=description, visibility=visibility
    )


@transaction.atomic
def update_collection(*, collection: Collection, user: User, data: dict) -> Collection:
    if "editors" in data and collection.owner_id != user.pk:
        raise DomainError(
            code="forbidden", message="Редакторів призначає лише власник.", status=403
        )
    words.check(title=data.get("title", ""), description=data.get("description", ""))
    for name in ("title", "description", "visibility"):
        if name in data:
            setattr(collection, name, data[name])
    collection.save()
    if "editors" in data:
        _set_editors(collection, data["editors"])
    return collection


def delete_collection(*, collection: Collection, user: User) -> None:
    if collection.owner_id != user.pk:
        raise DomainError(code="forbidden", message="Видалити може лише власник.", status=403)
    collection.delete()


@transaction.atomic
def add_item(
    *,
    collection: Collection,
    user: User,
    kind: str,
    identifier: str,
    note: str = "",
    slot: str = "",
) -> CollectionItem:
    kind_obj, target = kinds.resolve(kind, identifier, viewer=user, action="collect")
    item = CollectionItem.objects.filter(
        collection=collection, content_type=kind_obj.content_type, object_id=target.pk
    ).first()
    if item:
        return item
    position = (collection.items.aggregate(top=Max("position"))["top"] or 0) + 1
    try:
        with transaction.atomic():
            item = CollectionItem.objects.create(
                collection=collection,
                content_type=kind_obj.content_type,
                object_id=target.pk,
                position=position,
                note=note,
                slot=slot,
                added_by=user,
            )
    except IntegrityError:  # added concurrently
        return CollectionItem.objects.get(
            collection=collection, content_type=kind_obj.content_type, object_id=target.pk
        )
    bump(collection, "items_count", 1)
    collection.save(update_fields=["updated_at"])
    return item


@transaction.atomic
def remove_item(*, collection: Collection, item_id: int) -> None:
    deleted, _ = collection.items.filter(pk=item_id).delete()
    if not deleted:
        raise DomainError(code="not_found", message="Такого елемента немає.", status=404)
    bump(collection, "items_count", -1)
    collection.save(update_fields=["updated_at"])


@transaction.atomic
def reorder_items(*, collection: Collection, item_ids: list[int]) -> None:
    """New order of all items; ids must be exactly the collection's items."""
    current = set(collection.items.values_list("pk", flat=True))
    if set(item_ids) != current or len(item_ids) != len(current):
        raise DomainError(
            code="invalid_order",
            message="Порядок має містити всі елементи колекції рівно по разу.",
            fields={"item_ids": ["Передай усі елементи колекції без повторів."]},
        )
    items = {item.pk: item for item in collection.items.all()}
    for position, item_id in enumerate(item_ids, start=1):
        items[item_id].position = position
    CollectionItem.objects.bulk_update(items.values(), ["position"])
    collection.save(update_fields=["updated_at"])


@transaction.atomic
def copy_collection(*, source: Collection, user: User) -> Collection:
    """A private copy for the user with the same items and notes."""
    title = source.title[: 80 - len(COPY_SUFFIX)] + COPY_SUFFIX
    copy = Collection.objects.create(
        owner=user,
        title=title,
        description=source.description,
        visibility=Collection.Visibility.PRIVATE,
        copied_from=source,
        is_setup=source.is_setup,
    )
    items = [
        CollectionItem(
            collection=copy,
            content_type_id=item.content_type_id,
            object_id=item.object_id,
            position=item.position,
            slot=item.slot,
            note=item.note,
            added_by=user,
        )
        for item in source.items.all()
    ]
    CollectionItem.objects.bulk_create(items)
    Collection.objects.filter(pk=copy.pk).update(items_count=len(items))
    copy.refresh_from_db()
    return copy
