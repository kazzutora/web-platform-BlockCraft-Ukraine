from django.apps import AppConfig


class CompatConfig(AppConfig):
    """Compatibility engine (tech.md 9): pure functions and the API around them, no models."""

    name = "apps.compat"
    label = "compat"
    verbose_name = "Сумісність"
