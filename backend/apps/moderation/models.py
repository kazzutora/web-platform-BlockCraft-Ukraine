from django.conf import settings
from django.db import models

from apps.core.models import GenericTarget


class Report(GenericTarget):
    class Reason(models.TextChoices):
        INAPPROPRIATE = "inappropriate", "Неприйнятний вміст"
        SPAM = "spam", "Спам або реклама"
        STOLEN = "stolen", "Чужа робота"
        SCAM = "scam", "Шахрайство"
        OTHER = "other", "Інше"

    class Status(models.TextChoices):
        NEW = "new", "Нова"
        ACCEPTED = "accepted", "Прийнята"
        REJECTED = "rejected", "Відхилена"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports"
    )
    reason = models.CharField("причина", max_length=16, choices=Reason.choices)
    comment = models.CharField("коментар", max_length=500, blank=True)
    status = models.CharField(
        "статус", max_length=16, choices=Status.choices, default=Status.NEW, db_index=True
    )
    #: The object went hidden automatically after enough open reports
    auto_hidden = models.BooleanField("приховано автоматично", default=False)
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="розглянув",
    )
    handled_at = models.DateTimeField("розглянуто", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "скарга"
        verbose_name_plural = "скарги"
        ordering = ["-created_at"]
        constraints = [
            # One open report per player and object; after a decision they may report again
            models.UniqueConstraint(
                fields=["reporter", "content_type", "object_id"],
                condition=models.Q(status="new"),
                name="moderation_one_open_report",
            )
        ]
        indexes = [
            models.Index(
                fields=["content_type", "object_id", "status"], name="moderation_report_target"
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_reason_display()} · {self.content_type.model} {self.object_id}"


class Sanction(models.Model):
    class Type(models.TextChoices):
        WARNING = "warning", "Попередження"
        PUBLISH_BAN = "publish_ban", "Заборона публікацій"
        BAN = "ban", "Бан"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sanctions"
    )
    type = models.CharField("тип", max_length=16, choices=Type.choices)
    until = models.DateTimeField("до", null=True, blank=True, help_text="Порожньо — назавжди.")
    reason = models.CharField("причина", max_length=280)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="видав",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "санкція"
        verbose_name_plural = "санкції"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_type_display()} · {self.user}"


class BannedWord(models.Model):
    class Language(models.TextChoices):
        UK = "uk", "Українська"
        RU = "ru", "Російська"
        EN = "en", "Англійська"

    word = models.CharField("слово", max_length=32, unique=True)
    language = models.CharField("мова", max_length=2, choices=Language.choices)
    is_root = models.BooleanField(
        "корінь",
        default=True,
        help_text="Корінь шукається всередині слів; інакше — лише слово цілком.",
    )

    class Meta:
        verbose_name = "заборонене слово"
        verbose_name_plural = "заборонені слова"
        ordering = ["language", "word"]

    def __str__(self) -> str:
        return self.word

    def save(self, *args, **kwargs) -> None:
        self.word = self.word.strip().lower()
        super().save(*args, **kwargs)
