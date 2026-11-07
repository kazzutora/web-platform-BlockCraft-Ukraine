from django.contrib import admin

from .models import SyncRun


@admin.register(SyncRun)
class SyncRunAdmin(admin.ModelAdmin):
    """Read-only journal: runs are written by `sync_run(...)` only."""

    list_display = [
        "job",
        "source",
        "status",
        "started_at",
        "duration",
        "created",
        "updated",
        "unchanged",
        "skipped",
        "failed",
    ]
    list_filter = ["source", "status"]
    search_fields = ["job"]
    date_hierarchy = "started_at"

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    @admin.display(description="тривалість")
    def duration(self, obj: SyncRun):
        return obj.duration
