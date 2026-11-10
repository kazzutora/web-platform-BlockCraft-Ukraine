from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest

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
    fields = ["version_number", "version_type", "game_versions", "loaders", "date_published"]
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


FROM_SOURCE = [
    "source",
    "external_id",
    "external_url",
    "icon_url",
    "loaders",
    "game_versions",
    "client_side",
    "server_side",
    "license",
    "source_url",
    "modrinth_downloads",
    "modrinth_follows",
    "published_at",
    "modrinth_updated_at",
    "synced_at",
    "versions_synced_at",
]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "project_type",
        "is_hidden",
        "gpu_load",
        "modrinth_downloads",
        "synced_at",
    ]
    list_filter = ["is_hidden", "project_type", "gpu_load", NeedsTranslationFilter]
    search_fields = ["title", "slug", "external_id"]
    readonly_fields = ["slug", "project_type", "title", "summary", "imported_by", *FROM_SOURCE]
    fieldsets = [
        (None, {"fields": ["title", "slug", "project_type", "is_hidden", "hidden_reason"]}),
        ("Для гравців", {"fields": ["summary_uk", "summary", "gpu_load", "gpu_load_manual"]}),
        ("З Modrinth", {"classes": ["collapse"], "fields": FROM_SOURCE}),
        ("Хто додав", {"fields": ["imported_by"]}),
    ]
    inlines = [ProjectVersionInline]
    actions = ["hide_projects", "show_projects"]

    def save_model(self, request: HttpRequest, obj: Project, form, change: bool) -> None:
        # A moderator who touches GPU load decides it; sync keeps it afterwards
        if "gpu_load" in form.changed_data:
            obj.gpu_load_manual = True
        super().save_model(request, obj, form, change)

    @admin.action(description="Приховати з каталогу")
    def hide_projects(self, request: HttpRequest, queryset: QuerySet[Project]) -> None:
        # One by one: save() tells the search index the project left
        for project in queryset:
            project.is_hidden = True
            project.save(update_fields=["is_hidden"])
        self.message_user(request, f"Приховано: {queryset.count()}", messages.SUCCESS)

    @admin.action(description="Повернути в каталог")
    def show_projects(self, request: HttpRequest, queryset: QuerySet[Project]) -> None:
        for project in queryset:
            project.is_hidden = False
            project.hidden_reason = ""
            project.save(update_fields=["is_hidden", "hidden_reason"])
        self.message_user(request, f"Повернуто: {queryset.count()}", messages.SUCCESS)
