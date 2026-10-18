from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest

from apps.core import publishing

from .models import Server

DEFAULT_REJECTION = "Сервер не відповідає правилам каталогу."


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "address",
        "author",
        "edition",
        "status",
        "is_verified",
        "last_online_at",
    ]
    list_filter = ["status", "edition", "language", "is_verified"]
    search_fields = ["name", "slug", "host", "author__nickname"]
    raw_id_fields = ["author"]
    readonly_fields = [
        "verify_code",
        "last_online_at",
        "ip_copies_count",
        "rating_avg",
        "rating_count",
        "favorites_count",
        "comments_count",
        "published_at",
    ]
    actions = ["approve_servers", "reject_servers"]

    @admin.action(description="Схвалити й опублікувати")
    def approve_servers(self, request: HttpRequest, queryset: QuerySet[Server]) -> None:
        for server in queryset:
            publishing.set_status(server, Server.Status.PUBLISHED)
        self.message_user(request, f"Опубліковано: {queryset.count()}", messages.SUCCESS)

    @admin.action(description="Відхилити (стандартна причина)")
    def reject_servers(self, request: HttpRequest, queryset: QuerySet[Server]) -> None:
        for server in queryset:
            publishing.set_status(server, Server.Status.REJECTED, reason=DEFAULT_REJECTION)
        self.message_user(request, f"Відхилено: {queryset.count()}", messages.SUCCESS)
