from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.models import Authored, GenericTarget, TimeStamped

SUMMARY_MAX = 300
DESCRIPTION_MAX = 20_000


class Translation(GenericTarget, TimeStamped, Authored):
    """A player's Ukrainian text for something from a source (tech.md 6.9).

    Premoderated: a moderator approves it, then it is copied onto the target
    (`summary_uk` / `body_uk_html` + who translated) and the previous one is superseded.
    """

    class Field(models.TextChoices):
        SUMMARY = "summary", "Короткий опис"
        DESCRIPTION = "description", "Опис"

    class Status(models.TextChoices):
        PENDING = "pending", "Чекає модератора"
        PUBLISHED = "published", "Опубліковано"
        REJECTED = "rejected", "Відхилено"
        SUPERSEDED = "superseded", "Замінено новішим"

    field = models.CharField("що перекладено", max_length=12, choices=Field.choices)
    #: Plain text for the summary, markdown for the description
    text = models.TextField("переклад", max_length=DESCRIPTION_MAX)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="модератор",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reject_reason = models.CharField("чому відхилено", max_length=280, blank=True)

    class Meta:
        verbose_name = "переклад"
        verbose_name_plural = "переклади"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["author", "content_type", "object_id", "field"],
                condition=Q(status="pending"),
                name="translations_one_pending_per_author",
            ),
            models.UniqueConstraint(
                fields=["content_type", "object_id", "field"],
                condition=Q(status="published"),
                name="translations_one_published",
            ),
        ]
        indexes = [
            models.Index(fields=["content_type", "object_id", "status"], name="translations_target")
        ]

    def __str__(self) -> str:
        return f"{self.get_field_display()} → {self.content_type.model}#{self.object_id}"
