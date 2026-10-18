from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest

from . import services
from .models import BannedWord, Report, Sanction


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """The report queue: decide for every object once, all its open reports close together."""

    list_display = ["target_link", "reason", "reporter", "status", "auto_hidden", "created_at"]
    list_filter = ["status", "reason", "auto_hidden", "content_type"]
    search_fields = ["reporter__nickname", "comment"]
    readonly_fields = [
        "reporter",
        "content_type",
        "object_id",
        "reason",
        "comment",
        "auto_hidden",
        "handled_by",
        "handled_at",
        "created_at",
    ]
    fields = [*readonly_fields, "status"]
    actions = ["accept", "reject"]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Report]:
        return super().get_queryset(request).select_related("reporter", "content_type")

    @admin.display(description="об'єкт")
    def target_link(self, report: Report) -> str:
        return str(report.target) if report.target is not None else "— видалено —"

    @admin.action(description="Прийняти: приховати об'єкт і сповістити автора")
    def accept(self, request: HttpRequest, queryset: QuerySet[Report]) -> None:
        count = services.accept_reports(reports=queryset, moderator=request.user)
        self.message_user(request, f"Приховано об'єктів: {count}", messages.SUCCESS)

    @admin.action(description="Відхилити: залишити об'єкт (повернути, якщо приховано)")
    def reject(self, request: HttpRequest, queryset: QuerySet[Report]) -> None:
        count = services.reject_reports(reports=queryset, moderator=request.user)
        self.message_user(request, f"Залишено об'єктів: {count}", messages.SUCCESS)


@admin.register(Sanction)
class SanctionAdmin(admin.ModelAdmin):
    list_display = ["user", "type", "until", "reason", "issued_by", "created_at"]
    list_filter = ["type"]
    search_fields = ["user__nickname", "reason"]
    raw_id_fields = ["user"]
    readonly_fields = ["issued_by", "created_at"]

    def save_model(self, request: HttpRequest, obj: Sanction, form, change: bool) -> None:
        if change:
            super().save_model(request, obj, form, change)
            return
        # New sanctions go through the service: a ban deactivates, a warning notifies
        services.issue_sanction(
            user=obj.user, type=obj.type, reason=obj.reason, until=obj.until, moderator=request.user
        )


@admin.register(BannedWord)
class BannedWordAdmin(admin.ModelAdmin):
    list_display = ["word", "language", "is_root"]
    list_filter = ["language", "is_root"]
    search_fields = ["word"]
