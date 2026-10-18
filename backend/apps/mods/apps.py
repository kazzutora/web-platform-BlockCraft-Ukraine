from django.apps import AppConfig


class ModsConfig(AppConfig):
    name = "apps.mods"
    label = "mods"
    verbose_name = "Моди"

    def ready(self) -> None:
        from apps.core import kinds

        kinds.register(
            kinds.Kind(
                name="mod",
                model_label="mods.Project",
                lookup_field="slug",
                rating="review",
                actions=frozenset({"favorite", "review", "comment", "collect", "report"}),
                owner_field="claimed_by",
            )
        )
