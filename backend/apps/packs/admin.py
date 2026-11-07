from django.contrib import admin

from .models import LoaderRelease, Pack, PackItem


class PackItemInline(admin.TabularInline):
    model = PackItem
    extra = 0
    raw_id_fields = ["project", "version"]
    fields = ["project", "version", "is_required", "added_as_dependency", "position"]


@admin.register(Pack)
class PackAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "game_version", "loader", "is_official", "status"]
    list_filter = ["status", "is_official", "loader", "game_version"]
    search_fields = ["title", "slug", "author__nickname"]
    raw_id_fields = ["author", "forked_from"]
    readonly_fields = [
        "install_html",
        "changelog_html",
        "modrinth_id",
        "modrinth_version_id",
        "source_file_url",
        "forks_count",
        "rating_avg",
        "rating_count",
        "favorites_count",
        "downloads_count",
        "published_at",
    ]
    inlines = [PackItemInline]


@admin.register(LoaderRelease)
class LoaderReleaseAdmin(admin.ModelAdmin):
    list_display = ["loader", "game_version", "version", "updated_at"]
    list_filter = ["loader"]
