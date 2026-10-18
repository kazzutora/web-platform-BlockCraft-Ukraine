from django.apps import AppConfig


class SearchConfig(AppConfig):
    name = "apps.search"
    label = "search"
    verbose_name = "Пошук"

    def ready(self) -> None:
        from apps.core import kinds

        from . import signals

        # Saved and deleted objects of every kind reach the index through Celery
        kinds.on_register(signals.watch_kind)
