from django.apps import AppConfig


class PacksConfig(AppConfig):
    name = "apps.packs"
    label = "packs"
    verbose_name = "Зборки"

    def ready(self) -> None:
        from apps.core import kinds

        kinds.register(
            kinds.Kind(
                name="pack",
                model_label="packs.Pack",
                lookup_field="slug",
                rating="review",
                actions=frozenset({"favorite", "review", "collect", "report"}),
                owner_field="author",
            )
        )
