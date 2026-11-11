from django.apps import AppConfig


class ServersConfig(AppConfig):
    name = "apps.servers"
    label = "servers"
    verbose_name = "Сервери"

    def ready(self) -> None:
        from apps.core import kinds

        from .models import Server

        kinds.register(
            kinds.Kind(
                name="server",
                model_label="servers.Server",
                lookup_field="slug",
                rating="review",
                actions=frozenset({"favorite", "review", "collect", "report"}),
                owner_field="owner",
                visible=lambda viewer: Server.objects.listed(),
            )
        )
