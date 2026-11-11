from django.contrib import admin

from .models import Server


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "address",
        "source",
        "owner",
        "content_kind",
        "is_verified",
        "is_hidden",
        "last_online_at",
    ]
    list_filter = ["source", "content_kind", "is_verified", "is_hidden", "country"]
    search_fields = ["name", "slug", "java_host", "bedrock_host", "owner__nickname", "external_id"]
    raw_id_fields = ["owner", "claimant", "required_pack"]
    readonly_fields = [
        "source",
        "external_id",
        "external_url",
        "synced_at",
        "description_html",
        "description_uk_html",
        "last_online_at",
        "modrinth_plays",
        "ip_copies_count",
        "rating_avg",
        "rating_count",
        "favorites_count",
    ]
