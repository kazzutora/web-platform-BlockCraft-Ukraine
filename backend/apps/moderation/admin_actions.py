"""Moderation actions shared by the admin pages of skins, servers and other publications."""

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.db.models import QuerySet
from django.http import HttpRequest
from django.template.response import TemplateResponse

from . import services

DEFAULT_REJECTION = "Не відповідає правилам спільноти."


class RejectForm(forms.Form):
    reason = forms.CharField(
        label="Причина (її побачить автор)",
        max_length=280,
        initial=DEFAULT_REJECTION,
        widget=forms.Textarea(attrs={"rows": 3, "cols": 60}),
    )


class PublicationModerationMixin:
    """Adds «Схвалити й опублікувати» and «Відхилити з причиною…» to a ModelAdmin."""

    actions = ["approve_selected", "reject_selected"]

    @admin.action(description="Схвалити й опублікувати")
    def approve_selected(self, request: HttpRequest, queryset: QuerySet) -> None:
        for obj in queryset:
            services.approve(obj=obj, moderator=request.user)
        self.message_user(request, f"Опубліковано: {queryset.count()}", messages.SUCCESS)

    @admin.action(description="Відхилити з причиною…")
    def reject_selected(self, request: HttpRequest, queryset: QuerySet):
        form = RejectForm(request.POST if "apply" in request.POST else None)
        if form.is_valid():
            for obj in queryset:
                services.reject(obj=obj, reason=form.cleaned_data["reason"], moderator=request.user)
            self.message_user(request, f"Відхилено: {queryset.count()}", messages.SUCCESS)
            return None
        return TemplateResponse(
            request,
            "admin/moderation/reject.html",
            {
                **self.admin_site.each_context(request),
                "title": "Причина відхилення",
                "objects": queryset,
                "form": form,
                "action": "reject_selected",
                "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
                "opts": self.model._meta,
            },
        )
