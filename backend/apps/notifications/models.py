from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        APPROVED = "approved", "Роботу опубліковано"
        REJECTED = "rejected", "Роботу відхилено"
        HIDDEN = "hidden", "Роботу приховано після скарг"
        RESTORED = "restored", "Роботу повернуто"
        REPLY = "reply", "Відповідь на коментар"
        REVIEW = "review", "Новий відгук"
        WARNING = "warning", "Попередження"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    type = models.CharField(max_length=16, choices=Type.choices)
    #: {kind, id, title, reason, actor, excerpt}: what the text and the link need
    payload = models.JSONField(default=dict)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "сповіщення"
        verbose_name_plural = "сповіщення"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "-created_at"], name="notif_user_read_created")
        ]

    def __str__(self) -> str:
        return f"{self.get_type_display()} → {self.user_id}"
