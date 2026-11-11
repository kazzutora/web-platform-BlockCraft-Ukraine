import django_filters
from django.db.models import Q, QuerySet

from apps.core.models import Source

from .models import Skin
from .styles import ColorBucket

SORTS = {
    "popular": ["-favorites_count", "-downloads_count", "-source_views"],
    "new": ["-created_at"],
    "top": ["-favorites_count", "-downloads_count"],
    "trend": ["-trend_score", "-favorites_count"],
}
SKIN_SOURCES = [(Source.MINESKIN.value, "MineSkin"), (Source.MOJANG.value, "Mojang")]


class SkinFilter(django_filters.FilterSet):
    color = django_filters.ChoiceFilter(field_name="color_bucket", choices=ColorBucket.choices)
    model = django_filters.ChoiceFilter(choices=Skin.Model.choices)
    source = django_filters.ChoiceFilter(choices=SKIN_SOURCES)
    q = django_filters.CharFilter(method="filter_q", help_text="Title or player nickname.")
    sort = django_filters.ChoiceFilter(
        method="filter_sort", choices=[(key, key) for key in SORTS], empty_label=None
    )

    class Meta:
        model = Skin
        fields = ["color", "model", "source", "q", "sort"]

    @property
    def qs(self) -> QuerySet[Skin]:
        queryset = super().qs
        if not self.form.cleaned_data.get("sort"):
            queryset = queryset.order_by(*SORTS["popular"])
        return queryset

    def filter_q(self, queryset, name, value: str):
        value = value.strip()
        return queryset.filter(Q(title__icontains=value) | Q(player_name__iexact=value))

    def filter_sort(self, queryset, name, value: str):
        return queryset.order_by(*SORTS[value])
