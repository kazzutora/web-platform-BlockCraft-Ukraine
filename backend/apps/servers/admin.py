from django.contrib import admin

from apps.moderation.admin_actions import PublicationModerationMixin

from .models import Server


@admin.register(Server)
class ServerAdmin(PublicationModerationMixin, admin.ModelAdmin):
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
