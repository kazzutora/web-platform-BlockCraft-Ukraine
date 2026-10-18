"""Abstract building blocks for content models (see docs/tech.md, 5.1)."""

from django.conf import settings
from django.db import models


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Authored(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+", verbose_name="автор"
    )

    class Meta:
        abstract = True


class PublishableQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Publishable.Status.PUBLISHED)


class Publishable(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Чернетка"
        PENDING = "pending", "На модерації"
        PUBLISHED = "published", "Опубліковано"
        REJECTED = "rejected", "Відхилено"
        HIDDEN = "hidden", "Приховано"

    status = models.CharField(
        "статус", max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    rejection_reason = models.CharField("причина відхилення", max_length=280, blank=True)
    published_at = models.DateTimeField("опубліковано", null=True, blank=True)

    objects = PublishableQuerySet.as_manager()

    class Meta:
        abstract = True


class Engagement(models.Model):
    """Denormalized counters; change them only in services with F() inside a transaction."""

    likes_count = models.PositiveIntegerField(default=0)
    favorites_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    downloads_count = models.PositiveIntegerField(default=0)
    views_count = models.PositiveIntegerField(default=0)
    rating_avg = models.FloatField(default=0)
    rating_count = models.PositiveIntegerField(default=0)
    score = models.FloatField("рейтинг (байєсівський)", default=0, db_index=True)
    trend_score = models.FloatField("тренд", default=0, db_index=True)

    class Meta:
        abstract = True
