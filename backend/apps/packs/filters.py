import django_filters
from django.db.models import Q, QuerySet
from django.db.models.functions import Lower

from apps.core.game import GAME_VERSION_CHOICES

from .choices import PackLoader, Style
from .models import Pack

SORTS = {
    "popular": ["-score", "-favorites_count", "-modrinth_downloads"],
    "new": ["-published_at"],
    "top": ["-score", "-rating_count"],
    "trend": ["-trend_score", "-score"],
    "downloads": ["-downloads_count", "-modrinth_downloads"],
}


class PackFilter(django_filters.FilterSet):
    game_version = django_filters.ChoiceFilter(choices=GAME_VERSION_CHOICES)
    loader = django_filters.ChoiceFilter(choices=PackLoader.choices)
    style = django_filters.CharFilter(
        method="filter_style", help_text="Style slugs, comma-separated; any may match."
    )
    official = django_filters.BooleanFilter(field_name="is_official")
    author = django_filters.CharFilter(method="filter_author", help_text="Author nickname.")
    q = django_filters.CharFilter(method="filter_q")
    sort = django_filters.ChoiceFilter(
        method="filter_sort", choices=[(key, key) for key in SORTS], empty_label=None
    )

    class Meta:
        model = Pack
        fields = ["game_version", "loader", "style", "official", "author", "q", "sort"]

    @property
    def qs(self) -> QuerySet[Pack]:
        queryset = super().qs
        if not self.form.cleaned_data.get("sort"):
            queryset = queryset.order_by(*SORTS["popular"])
        return queryset

    def filter_style(self, queryset, name, value: str):
        styles = [part for part in (p.strip() for p in value.split(",")) if part in Style.values]
        return queryset.filter(style_tags__overlap=styles) if styles else queryset

    def filter_author(self, queryset, name, value: str):
        return queryset.alias(owner_nickname=Lower("author__nickname")).filter(
            owner_nickname=value.lower()
        )

    def filter_q(self, queryset, name, value: str):
        return queryset.filter(Q(title__icontains=value) | Q(summary__icontains=value))

    def filter_sort(self, queryset, name, value: str):
        return queryset.order_by(*SORTS[value])
