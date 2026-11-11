from django.apps import AppConfig


class SkinsConfig(AppConfig):
    name = "apps.skins"
    label = "skins"
    verbose_name = "Скіни"

    def ready(self) -> None:
        from apps.core import kinds

        from .models import Skin

        kinds.register(
            kinds.Kind(
                name="skin",
                model_label="skins.Skin",
                lookup_field="pk",
                rating="favorites",
                actions=frozenset({"favorite", "collect", "report"}),
                visible=lambda viewer: Skin.objects.visible(),
            )
        )
