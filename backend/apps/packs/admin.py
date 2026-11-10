from django.contrib import admin

from .models import LoaderRelease, Pack, PackExternalFile, PackItem


class PackItemInline(admin.TabularInline):
    model = PackItem
    extra = 0
    raw_id_fields = ["project", "version"]
    fields = ["project", "version", "reason", "required_by", "env_client", "env_server", "position"]


class PackExternalFileInline(admin.TabularInline):
    model = PackExternalFile
    extra = 0
    fields = ["path", "url", "size"]
    readonly_fields = fields
    can_delete = False


@admin.register(Pack)
class PackAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "origin",
        "author",
        "game_version",
        "loader",
        "status",
        "visibility",
        "compat_status",
    ]
    list_filter = ["origin", "status", "visibility", "compat_status", "loader", "game_version"]
    search_fields = ["title", "slug", "author__nickname", "external_id"]
    raw_id_fields = ["author", "forked_from"]
    readonly_fields = [
        "notes_html",
        "description_html",
        "external_id",
        "external_url",
        "modrinth_version_id",
        "source_file_url",
        "compat_report",
        "compat_checked_at",
        "items_count",
        "forks_count",
        "rating_avg",
        "rating_count",
        "favorites_count",
        "downloads_count",
        "published_at",
        "synced_at",
    ]
    inlines = [PackItemInline, PackExternalFileInline]


@admin.register(LoaderRelease)
class LoaderReleaseAdmin(admin.ModelAdmin):
    list_display = ["loader", "game_version", "version", "updated_at"]
    list_filter = ["loader"]
