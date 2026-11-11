from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import GenericTarget, TimeStamped


class Review(GenericTarget, TimeStamped):
    class Status(models.TextChoices):
        PUBLISHED = "published", "Опубліковано"
        HIDDEN = "hidden", "Приховано"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    stars = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    text = models.TextField(max_length=1000, blank=True)
    helpful_count = models.PositiveIntegerField(default=0)
    #: The author of the pack or the proven owner of the server answers, once (editable)
    reply_text = models.TextField("відповідь", max_length=500, blank=True)
    reply_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="хто відповів",
    )
    replied_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PUBLISHED, db_index=True
    )

    class Meta:
        verbose_name = "відгук"
        verbose_name_plural = "відгуки"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "content_type", "object_id"], name="social_review_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(stars__gte=1, stars__lte=5), name="social_review_stars_1_5"
            ),
        ]
        indexes = [
            models.Index(
                fields=["content_type", "object_id", "status"], name="social_review_target"
            )
        ]

    def __str__(self) -> str:
        return f"{self.user}: {self.stars}★ {self.content_type.model}#{self.object_id}"


class ReviewVote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="votes")
    is_helpful = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "оцінка відгуку"
        verbose_name_plural = "оцінки відгуків"
        constraints = [
            models.UniqueConstraint(fields=["user", "review"], name="social_review_vote_unique")
        ]

    def __str__(self) -> str:
        return f"{self.user} → {self.review_id}: {'+' if self.is_helpful else '-'}"
