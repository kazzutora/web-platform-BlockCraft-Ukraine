from django.contrib import admin
from django.utils.html import format_html

from apps.moderation.admin_actions import PublicationModerationMixin

from .models import Skin


@admin.register(Skin)
class SkinAdmin(PublicationModerationMixin, admin.ModelAdmin):
    list_display = ["thumbnail", "title", "author", "status", "model", "color_bucket", "created_at"]
    list_display_links = ["thumbnail", "title"]
    list_filter = ["status", "model", "color_bucket"]
    search_fields = ["title", "author__nickname"]
    raw_id_fields = ["author", "parent"]
    readonly_fields = [
        "thumbnail",
        "texture_hash",
        "dominant_color",
        "likes_count",
        "favorites_count",
        "downloads_count",
        "comments_count",
        "published_at",
    ]

    @admin.display(description="прев'ю")
    def thumbnail(self, skin: Skin) -> str:
        image = skin.preview or skin.file
        if not image:
            return "—"
        return format_html(
            '<img src="{}" alt="" width="32" style="image-rendering: pixelated">', image.url
        )
