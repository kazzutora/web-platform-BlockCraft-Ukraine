from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import GenericTarget, Publishable, TimeStamped


class Like(GenericTarget):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="likes"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "вподобання"
        verbose_name_plural = "вподобання"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "content_type", "object_id"], name="social_like_unique"
            )
        ]
        indexes = [models.Index(fields=["content_type", "object_id"], name="social_like_target")]

    def __str__(self) -> str:
        return f"{self.user} ♥ {self.content_type.model}#{self.object_id}"


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


class Comment(GenericTarget, TimeStamped, Publishable):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments"
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )
    body = models.TextField(max_length=1000)
    is_pinned = models.BooleanField(default=False)
    #: Deleted comments with replies stay as «коментар видалено» so the thread keeps sense
    is_deleted = models.BooleanField(default=False)

    class Meta:
        verbose_name = "коментар"
        verbose_name_plural = "коментарі"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["content_type", "object_id", "parent", "created_at"],
                name="social_comment_target",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user}: {self.body[:40]}"
