from django.apps import AppConfig


class LibraryConfig(AppConfig):
    name = "apps.library"
    label = "library"
    verbose_name = "Бібліотека"

    def ready(self) -> None:
        from apps.core import kinds

        from . import selectors

        kinds.register(
            kinds.Kind(
                name="collection",
                model_label="library.Collection",
                lookup_field="pk",
                rating="like",
                actions=frozenset({"favorite", "like", "comment", "report"}),
                owner_field="owner",
                visible=selectors.listed_collections,
            )
        )
