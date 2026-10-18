from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest

from . import services
from .models import Category, Project, ProjectVersion


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["slug", "name_uk", "project_type", "header"]
    list_filter = ["project_type", "header"]
    list_editable = ["name_uk"]
    search_fields = ["slug", "name_uk"]


class ProjectVersionInline(admin.TabularInline):
    model = ProjectVersion
    extra = 0
    can_delete = False
    fields = ["version_number", "version_type", "game_versions", "loaders", "released_at"]
    readonly_fields = fields
    show_change_link = False
    max_num = 0


class NeedsTranslationFilter(admin.SimpleListFilter):
    title = "опис українською"
    parameter_name = "translated"

    def lookups(self, request, model_admin):
        return [("no", "Немає"), ("yes", "Є")]

    def queryset(self, request, queryset):
        if self.value() == "no":
            return queryset.filter(summary_uk="")
        if self.value() == "yes":
            return queryset.exclude(summary_uk="")
        return queryset


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "project_type",
        "status",
        "gpu_load",
        "modrinth_downloads",
        "synced_at",
    ]
    list_filter = ["status", "project_type", "gpu_load", NeedsTranslationFilter]
    search_fields = ["title", "slug", "modrinth_id"]
    readonly_fields = [
        "modrinth_id",
        "slug",
        "project_type",
        "title",
        "summary",
        "icon_url",
        "loaders",
        "game_versions",
        "license",
        "source_url",
        "modrinth_downloads",
        "modrinth_updated_at",
        "synced_at",
        "suggested_by",
        "published_at",
    ]
    fieldsets = [
        (None, {"fields": ["title", "slug", "project_type", "status", "rejection_reason"]}),
        ("Для гравців", {"fields": ["summary_uk", "summary", "gpu_load", "gpu_load_manual"]}),
        (
            "З Modrinth",
            {
                "classes": ["collapse"],
                "fields": [
                    "modrinth_id",
                    "icon_url",
                    "loaders",
                    "game_versions",
                    "license",
                    "source_url",
                    "modrinth_downloads",
                    "modrinth_updated_at",
                    "synced_at",
                ],
            },
        ),
        ("Автори", {"fields": ["claimed_by", "suggested_by", "published_at"]}),
    ]
    raw_id_fields = ["claimed_by"]
    inlines = [ProjectVersionInline]
    actions = ["publish_projects", "hide_projects"]

    def save_model(self, request: HttpRequest, obj: Project, form, change: bool) -> None:
        # A moderator who touches GPU load decides it; sync keeps it afterwards
        if "gpu_load" in form.changed_data:
            obj.gpu_load_manual = True
        super().save_model(request, obj, form, change)

    @admin.action(description="Схвалити й опублікувати")
    def publish_projects(self, request: HttpRequest, queryset: QuerySet[Project]) -> None:
        for project in queryset:
            services.publish(project=project)
        self.message_user(request, f"Опубліковано: {queryset.count()}", messages.SUCCESS)

    @admin.action(description="Приховати з каталогу")
    def hide_projects(self, request: HttpRequest, queryset: QuerySet[Project]) -> None:
        updated = queryset.update(status=Project.Status.HIDDEN)
        self.message_user(request, f"Приховано: {updated}", messages.SUCCESS)
