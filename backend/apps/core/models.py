"""Abstract building blocks for content models (see docs/tech.md, 5.1)."""

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
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


class Source(models.TextChoices):
    """Where a catalog object comes from (the registry in apps/sources describes each one)."""

    MODRINTH = "modrinth", "Modrinth"
    MINESKIN = "mineskin", "MineSkin"
    MOJANG = "mojang", "Mojang"
    OWNER = "owner", "Власник"


class SourcedQuerySet(models.QuerySet):
    def visible(self):
        return self.filter(is_hidden=False)


class Sourced(models.Model):
    """Everything mirrored from a source: we keep the link back and never invent the object.

    Concrete models inherit `Meta` (`class Meta(Sourced.Meta)`) to get the unique
    `(source, external_id)` constraint.
    """

    source = models.CharField("джерело", max_length=16, choices=Source.choices, db_index=True)
    external_id = models.CharField("id у джерелі", max_length=64)
    external_url = models.URLField("сторінка в джерелі", max_length=500, blank=True)
    synced_at = models.DateTimeField("синхронізовано", null=True, blank=True)
    is_hidden = models.BooleanField("приховано в нас", default=False, db_index=True)
    hidden_reason = models.CharField("чому приховано", max_length=280, blank=True)

    objects = SourcedQuerySet.as_manager()

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"],
                name="%(app_label)s_%(class)s_source_external_id_unique",
            )
        ]


class Engagement(models.Model):
    """Denormalized counters; change them only in services with F() inside a transaction."""

    favorites_count = models.PositiveIntegerField(default=0)
    downloads_count = models.PositiveIntegerField(default=0)
    rating_avg = models.FloatField(default=0)
    rating_count = models.PositiveIntegerField(default=0)
    score = models.FloatField("рейтинг (байєсівський)", default=0, db_index=True)
    trend_score = models.FloatField("тренд", default=0, db_index=True)

    class Meta:
        abstract = True


class GenericTarget(models.Model):
    """`content_type` + `object_id` of any registered kind (see apps/core/kinds.py)."""

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name="+")
    object_id = models.PositiveBigIntegerField()
    target = GenericForeignKey("content_type", "object_id")

    class Meta:
        abstract = True
