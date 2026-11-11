"""Translations: players propose, a moderator approves, the target shows it with a byline."""

from django.db import transaction
from django.db.models import Model
from django.utils import timezone

from apps.accounts.models import User
from apps.core import kinds
from apps.core.exceptions import DomainError
from apps.moderation import services as moderation
from apps.moderation import words
from apps.mods.markdown import render_markdown
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import DESCRIPTION_MAX, SUMMARY_MAX, Translation

#: field → (text field on the target, who translated it)
TARGET_FIELDS = {
    Translation.Field.SUMMARY: ("summary_uk", "summary_uk_by"),
    Translation.Field.DESCRIPTION: ("body_uk_html", "body_uk_by"),
}
LIMITS = {Translation.Field.SUMMARY: SUMMARY_MAX, Translation.Field.DESCRIPTION: DESCRIPTION_MAX}


def translatable(kind: kinds.Kind, target: Model) -> bool:
    """Mods; packs and servers only when they come from Modrinth (ours are written here)."""
    if kind.name == "pack":
        return target.origin == "modrinth"
    if kind.name == "server":
        return target.source == "modrinth"
    return kind.allows("translate")


def resolve_target(*, kind: str, identifier: str, viewer) -> tuple[kinds.Kind, Model]:
    kind_obj, target = kinds.resolve(kind, identifier, viewer=viewer, action="translate")
    if not translatable(kind_obj, target):
        raise DomainError(code="not_translatable", message="Це пишуть тут, а не перекладають.")
    return kind_obj, target


@transaction.atomic
def propose(*, user: User, kind: str, identifier: str, field: str, text: str) -> Translation:
    """A player's translation waits for a moderator; a second one replaces their pending one."""
    kind_obj, target = resolve_target(kind=kind, identifier=identifier, viewer=user)
    moderation.ensure_can_publish(user)
    text = text.strip()
    if not text:
        message = "Переклад порожній."
        raise DomainError(code="invalid", message=message, fields={"text": [message]})
    if len(text) > LIMITS[field]:
        message = f"Не довше за {LIMITS[field]} символів."
        raise DomainError(code="invalid", message=message, fields={"text": [message]})
    words.check(text=text)
    translation, _ = Translation.objects.update_or_create(
        author=user,
        content_type=kind_obj.content_type,
        object_id=target.pk,
        field=field,
        status=Translation.Status.PENDING,
        defaults={"text": text},
    )
    return translation


@transaction.atomic
def review(
    *, translation: Translation, moderator: User, approve: bool, reason: str = ""
) -> Translation:
    """Approve: copied onto the target with a byline, the previous one superseded.
    Reject: the author hears why. Only pending translations are decided."""
    if not moderator.is_moderator:
        raise DomainError(code="forbidden", message="Рішення ухвалює модератор.", status=403)
    translation = Translation.objects.select_for_update().get(pk=translation.pk)
    if translation.status != Translation.Status.PENDING:
        raise DomainError(code="already_reviewed", message="Цей переклад уже розглянуто.")
    if translation.author_id == moderator.pk:
        raise DomainError(code="own_translation", message="Свій переклад схвалює інший модератор.")
    model = translation.content_type.model_class()
    # Locking the target: two approvals of one field never both become «published»
    target = model._base_manager.select_for_update().filter(pk=translation.object_id).first()
    if target is None:
        raise DomainError(code="not_found", message="Того, що перекладали, вже немає.", status=404)
    translation.reviewed_by = moderator
    translation.reviewed_at = timezone.now()
    if approve:
        Translation.objects.filter(
            content_type=translation.content_type,
            object_id=translation.object_id,
            field=translation.field,
            status=Translation.Status.PUBLISHED,
        ).update(status=Translation.Status.SUPERSEDED)
        translation.status = Translation.Status.PUBLISHED
        _apply(translation, target)
    else:
        translation.status = Translation.Status.REJECTED
        translation.reject_reason = reason.strip()[:280]
    translation.save()
    notify(
        user=translation.author,
        type=(
            Notification.Type.TRANSLATION_PUBLISHED
            if approve
            else Notification.Type.TRANSLATION_REJECTED
        ),
        target=target,
        reason=translation.reject_reason,
    )
    return translation


def _apply(translation: Translation, target: Model) -> None:
    text_field, by_field = TARGET_FIELDS[translation.field]
    value = (
        translation.text
        if translation.field == Translation.Field.SUMMARY
        else render_markdown(translation.text, images=False)
    )
    setattr(target, text_field, value)
    setattr(target, by_field, translation.author)
    # save(), not update(): the search index listens to post_save
    fields = [text_field, by_field]
    if hasattr(target, "updated_at"):
        fields.append("updated_at")
    target.save(update_fields=fields)
