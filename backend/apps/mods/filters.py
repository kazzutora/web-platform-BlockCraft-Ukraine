import django_filters
from django.db.models import Q, QuerySet

from .models import Project, ProjectType

SORTS = {
    "popular": ["-modrinth_downloads"],
    "new": ["-published_at"],
    "updated": ["-modrinth_updated_at"],
    "top": ["-score", "-modrinth_downloads"],
    "trend": ["-trend_score", "-modrinth_downloads"],
}


class ProjectFilter(django_filters.FilterSet):
    type = django_filters.ChoiceFilter(field_name="project_type", choices=ProjectType.choices)
    game_version = django_filters.CharFilter(method="filter_game_version")
    loader = django_filters.CharFilter(
        method="filter_loader", help_text="Applies to mods; resource packs and shaders pass."
    )
    category = django_filters.CharFilter(
        method="filter_category", help_text="Category slugs, comma-separated; all must match."
    )
    gpu_load = django_filters.ChoiceFilter(choices=Project.GpuLoad.choices)
    q = django_filters.CharFilter(method="filter_q")
    sort = django_filters.ChoiceFilter(
        method="filter_sort", choices=[(key, key) for key in SORTS], empty_label=None
    )

    class Meta:
        model = Project
        fields = ["type", "game_version", "loader", "category", "gpu_load", "q", "sort"]

    @property
    def qs(self) -> QuerySet[Project]:
        queryset = super().qs
        if not self.form.cleaned_data.get("sort"):
            queryset = queryset.order_by(*SORTS["popular"])
        return queryset

    def filter_game_version(self, queryset, name, value: str):
        return queryset.filter(game_versions__contains=[value])

    def filter_loader(self, queryset, name, value: str):
        return queryset.filter(~Q(project_type=ProjectType.MOD) | Q(loaders__contains=[value]))

    def filter_category(self, queryset, name, value: str):
        for slug in filter(None, (part.strip() for part in value.split(","))):
            queryset = queryset.filter(categories__slug=slug)
        return queryset.distinct()

    def filter_q(self, queryset, name, value: str):
        # Plain search until Meilisearch (stage 7)
        return queryset.filter(
            Q(title__icontains=value) | Q(summary__icontains=value) | Q(summary_uk__icontains=value)
        )

    def filter_sort(self, queryset, name, value: str):
        return queryset.order_by(*SORTS[value])
