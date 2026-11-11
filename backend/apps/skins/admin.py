from django.contrib import admin
from django.utils.html import format_html

from .models import Skin


@admin.register(Skin)
class SkinAdmin(admin.ModelAdmin):
    list_display = [
        "thumbnail",
        "title",
        "source",
        "model",
        "color_bucket",
        "is_hidden",
        "created_at",
    ]
    list_display_links = ["thumbnail", "title"]
    list_filter = ["source", "is_hidden", "model", "color_bucket"]
    search_fields = ["title", "player_name", "external_id"]
    raw_id_fields = ["added_by"]
    readonly_fields = [
        "thumbnail",
        "source",
        "external_id",
        "external_url",
        "texture_url",
        "texture_hash",
        "dominant_color",
        "source_views",
        "favorites_count",
        "downloads_count",
    ]

    @admin.display(description="прев'ю")
    def thumbnail(self, skin: Skin) -> str:
        image = skin.preview or skin.texture
        if not image:
            return "—"
        return format_html(
            '<img src="{}" alt="" width="32" style="image-rendering: pixelated">', image.url
        )
