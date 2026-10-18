from django.conf import settings
from django.db import models


class Download(models.Model):
    """A signed-in user took a file; used later to track updates of what they installed."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="downloads"
    )
    project = models.ForeignKey(
        "mods.Project", on_delete=models.CASCADE, related_name="user_downloads"
    )
    version = models.ForeignKey(
        "mods.ProjectVersion", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    game_version = models.CharField(max_length=32, blank=True)
    loader = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "завантаження"
        verbose_name_plural = "завантаження"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "project"], name="library_download_user_proj")]

    def __str__(self) -> str:
        return f"{self.user} ← {self.project}"
