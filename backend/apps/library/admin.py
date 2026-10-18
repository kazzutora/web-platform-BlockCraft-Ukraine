from django.contrib import admin

from .models import Collection, CollectionItem, Download, Favorite


class CollectionItemInline(admin.TabularInline):
    model = CollectionItem
    extra = 0
    fields = ["content_type", "object_id", "position", "slot", "note"]


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ["title", "owner", "visibility", "items_count", "likes_count", "updated_at"]
    list_filter = ["visibility", "is_setup"]
    search_fields = ["title", "owner__nickname"]
    raw_id_fields = ["owner", "copied_from"]
    filter_horizontal = ["editors"]
    readonly_fields = ["share_token", "items_count"]
    inlines = [CollectionItemInline]


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ["user", "content_type", "object_id", "created_at"]
    list_filter = ["content_type"]
    raw_id_fields = ["user"]


@admin.register(Download)
class DownloadAdmin(admin.ModelAdmin):
    list_display = ["user", "project", "game_version", "loader", "created_at"]
    list_filter = ["loader"]
    search_fields = ["user__nickname", "project__title"]
    raw_id_fields = ["user", "project", "version"]
