from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html

from . import services
from .models import Skin

DEFAULT_REJECTION = "Скін не відповідає правилам спільноти."


@admin.register(Skin)
class SkinAdmin(admin.ModelAdmin):
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
    actions = ["approve_skins", "reject_skins"]

    @admin.display(description="прев'ю")
    def thumbnail(self, skin: Skin) -> str:
        image = skin.preview or skin.file
        if not image:
            return "—"
        return format_html(
            '<img src="{}" alt="" width="32" style="image-rendering: pixelated">', image.url
        )

    @admin.action(description="Схвалити й опублікувати")
    def approve_skins(self, request: HttpRequest, queryset: QuerySet[Skin]) -> None:
        for skin in queryset:
            services.approve(skin=skin)
        self.message_user(request, f"Опубліковано: {queryset.count()}", messages.SUCCESS)

    @admin.action(description="Відхилити (стандартна причина)")
    def reject_skins(self, request: HttpRequest, queryset: QuerySet[Skin]) -> None:
        for skin in queryset:
            services.reject(skin=skin, reason=DEFAULT_REJECTION)
        self.message_user(request, f"Відхилено: {queryset.count()}", messages.SUCCESS)
