from django.contrib import admin

from .models import Download


@admin.register(Download)
class DownloadAdmin(admin.ModelAdmin):
    list_display = ["user", "project", "game_version", "loader", "created_at"]
    list_filter = ["loader"]
    search_fields = ["user__nickname", "project__title"]
    raw_id_fields = ["user", "project", "version"]
