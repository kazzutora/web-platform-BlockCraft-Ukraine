from django.db import models
from django.utils import timezone


class SyncRun(models.Model):
    """One synchronization job run: what it did and the first errors (see sources.runs)."""

    class Status(models.TextChoices):
        RUNNING = "running", "Виконується"
        OK = "ok", "Успішно"
        PARTIAL = "partial", "З помилками"
        FAILED = "failed", "Не вдалася"

    # Registry keys (sources.registry), not choices: a new source needs no migration
    source = models.CharField("джерело", max_length=32)
    job = models.CharField("задача", max_length=64)
    status = models.CharField(
        "статус", max_length=8, choices=Status.choices, default=Status.RUNNING
    )
    started_at = models.DateTimeField("почато", default=timezone.now)
    finished_at = models.DateTimeField("завершено", null=True, blank=True)
    created = models.PositiveIntegerField("створено", default=0)
    updated = models.PositiveIntegerField("оновлено", default=0)
    unchanged = models.PositiveIntegerField("без змін", default=0)
    skipped = models.PositiveIntegerField("пропущено", default=0)
    failed = models.PositiveIntegerField("помилок", default=0)
    errors = models.JSONField("приклади помилок", default=list, blank=True)
    params = models.JSONField("параметри", default=dict, blank=True)

    class Meta:
        verbose_name = "синхронізація"
        verbose_name_plural = "синхронізації"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["source", "-started_at"], name="sources_run_source_started")
        ]

    def __str__(self) -> str:
        return f"{self.job} · {self.started_at:%Y-%m-%d %H:%M} · {self.status}"

    @property
    def duration(self):
        return self.finished_at - self.started_at if self.finished_at else None
