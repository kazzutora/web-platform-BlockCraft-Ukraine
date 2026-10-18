from django.apps import AppConfig


class SkinsConfig(AppConfig):
    name = "apps.skins"
    label = "skins"
    verbose_name = "Скіни"

    def ready(self) -> None:
        from apps.core import kinds

        kinds.register(
            kinds.Kind(
                name="skin",
                model_label="skins.Skin",
                lookup_field="pk",
                rating="like",
                actions=frozenset({"favorite", "like", "comment", "collect", "report"}),
                owner_field="author",
            )
        )
