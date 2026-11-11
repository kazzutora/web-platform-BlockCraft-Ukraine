from django.contrib import admin, messages

from apps.core.exceptions import DomainError

from . import services
from .models import Translation


@admin.register(Translation)
class TranslationAdmin(admin.ModelAdmin):
    """The moderators' queue: approve or reject in bulk."""

    list_display = ["__str__", "author", "status", "created_at", "reviewed_by"]
    list_filter = ["status", "field", "content_type"]
    search_fields = ["text", "author__nickname"]
    raw_id_fields = ["author", "reviewed_by"]
    # Decisions go through the actions only: they copy the text onto the target and notify
    readonly_fields = [
        "content_type",
        "object_id",
        "field",
        "author",
        "text",
        "status",
        "reviewed_by",
        "reviewed_at",
        "reject_reason",
    ]
    actions = ["approve", "reject"]

    def _decide(self, request, queryset, *, approve: bool) -> None:
        done = 0
        for translation in queryset.filter(status=Translation.Status.PENDING):
            try:
                services.review(translation=translation, moderator=request.user, approve=approve)
            except DomainError as error:
                self.message_user(request, f"{translation}: {error.message}", messages.WARNING)
                continue
            done += 1
        self.message_user(request, f"Розглянуто: {done}", messages.SUCCESS)

    @admin.action(description="Схвалити")
    def approve(self, request, queryset) -> None:
        self._decide(request, queryset, approve=True)

    @admin.action(description="Відхилити")
    def reject(self, request, queryset) -> None:
        self._decide(request, queryset, approve=False)
