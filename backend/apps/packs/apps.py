from django.apps import AppConfig


class PacksConfig(AppConfig):
    name = "apps.packs"
    label = "packs"
    verbose_name = "Збірки"

    def ready(self) -> None:
        from apps.core import kinds

        from .selectors import listed

        kinds.register(
            kinds.Kind(
                name="pack",
                model_label="packs.Pack",
                lookup_field="slug",
                rating="review",
                actions=frozenset({"favorite", "review", "collect", "report", "translate"}),
                owner_field="author",
                # Saved, reviewed and reported only when anyone may open it
                visible=lambda viewer: listed(),
            )
        )
