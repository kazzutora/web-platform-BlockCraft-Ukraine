import django_filters
from django.db.models import QuerySet
from django.db.models.functions import Lower

from .models import Skin
from .styles import ColorBucket, Style

SORTS = {
    "popular": ["-downloads_count", "-likes_count"],
    "new": ["-published_at"],
    "top": ["-likes_count", "-downloads_count"],
    "trend": ["-trend_score", "-likes_count"],
}


class SkinFilter(django_filters.FilterSet):
    style = django_filters.CharFilter(
        method="filter_style", help_text="Style slugs, comma-separated; any may match."
    )
    color = django_filters.ChoiceFilter(field_name="color_bucket", choices=ColorBucket.choices)
    model = django_filters.ChoiceFilter(choices=Skin.Model.choices)
    author = django_filters.CharFilter(method="filter_author", help_text="Author nickname.")
    q = django_filters.CharFilter(field_name="title", lookup_expr="icontains")
    sort = django_filters.ChoiceFilter(
        method="filter_sort", choices=[(key, key) for key in SORTS], empty_label=None
    )

    class Meta:
        model = Skin
        fields = ["style", "color", "model", "author", "q", "sort"]

    @property
    def qs(self) -> QuerySet[Skin]:
        queryset = super().qs
        if not self.form.cleaned_data.get("sort"):
            queryset = queryset.order_by(*SORTS["popular"])
        return queryset

    def filter_style(self, queryset, name, value: str):
        styles = [part for part in (p.strip() for p in value.split(",")) if part in Style.values]
        return queryset.filter(style_tags__overlap=styles) if styles else queryset

    def filter_author(self, queryset, name, value: str):
        return queryset.alias(author_nickname=Lower("author__nickname")).filter(
            author_nickname=value.lower()
        )

    def filter_sort(self, queryset, name, value: str):
        return queryset.order_by(*SORTS[value])
