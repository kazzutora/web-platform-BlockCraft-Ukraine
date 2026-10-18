from django.apps import AppConfig


class SocialConfig(AppConfig):
    name = "apps.social"
    label = "social"
    verbose_name = "Спільнота"

    def ready(self) -> None:
        from apps.core import kinds

        from . import signals

        # Favorites, likes, reviews, comments and collection items of a deleted object go too
        kinds.on_register(signals.watch_deletions)
