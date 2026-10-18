from django.apps import AppConfig


class ModerationConfig(AppConfig):
    name = "apps.moderation"
    label = "moderation"
    verbose_name = "Модерація"

    def ready(self) -> None:
        from . import signals  # noqa: F401 — clears the cached word list on changes
