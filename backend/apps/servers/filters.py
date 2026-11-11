import django_filters
from django.db.models import F, Q, QuerySet
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field

from . import selectors
from .models import ContentKind, Server

SORTS = {
    "popular": ["-score", "-modrinth_plays", "-favorites_count"],
    "online": [F("live_players").desc(nulls_last=True), "-modrinth_plays"],
    "new": ["-created_at"],
    "top": ["-score", "-rating_count"],
    "trend": ["-trend_score", "-score"],
}


class ServerFilter(django_filters.FilterSet):
    """Without `language` the catalog shows Ukrainian-speaking servers while there are at
    least five of them; `language=` (empty) or `all=1` — every language."""

    language = django_filters.CharFilter(
        method="filter_noop", help_text="ISO 639-1; default «uk» if ≥ 5 such servers."
    )
    all = django_filters.BooleanFilter(method="filter_noop", help_text="1 — every language.")
    country = django_filters.CharFilter(method="filter_country", help_text="ISO 3166-1 alpha-2.")
    kind = django_filters.ChoiceFilter(field_name="content_kind", choices=ContentKind.choices)
    version = django_filters.CharFilter(method="filter_version", help_text="A game version.")
    category = django_filters.CharFilter(
        method="filter_category", help_text="Modrinth categories, comma-separated; any."
    )
    online = django_filters.BooleanFilter(method="filter_online", help_text="Online right now.")
    q = django_filters.CharFilter(method="filter_q")
    sort = django_filters.ChoiceFilter(
        method="filter_sort", choices=[(key, key) for key in SORTS], empty_label=None
    )

    class Meta:
        model = Server
        fields = [
            "language",
            "all",
            "country",
            "kind",
            "version",
            "category",
            "online",
            "q",
            "sort",
        ]

    def chosen_language(self) -> str:
        if str(self.data.get("all", "")).lower() in {"1", "true"}:
            return ""
        if "language" in self.data:
            return str(self.data.get("language") or "").strip().lower()
        return selectors.default_language()

    @property
    def qs(self) -> QuerySet[Server]:
        queryset = super().qs
        language = self.chosen_language()
        if language:
            queryset = queryset.filter(languages__contains=[language])
        if not self.form.cleaned_data.get("sort"):
            queryset = queryset.order_by(*SORTS["popular"])
        return queryset

    def _live(self, queryset: QuerySet[Server]) -> QuerySet[Server]:
        if "live_players" in queryset.query.annotations:
            return queryset
        return selectors.with_live(queryset)

    def filter_noop(self, queryset, name, value):
        return queryset

    def filter_country(self, queryset, name, value: str):
        return queryset.filter(country=value.strip().upper()[:2])

    def filter_version(self, queryset, name, value: str):
        value = value.strip()
        return queryset.filter(
            Q(supported_versions__contains=[value])
            | Q(recommended_version=value)
            | Q(required_pack__game_version=value)
        )

    def filter_category(self, queryset, name, value: str):
        wanted = [part.strip() for part in value.split(",") if part.strip()]
        return queryset.filter(categories__overlap=wanted) if wanted else queryset

    @extend_schema_field(OpenApiTypes.BOOL)
    def filter_online(self, queryset, name, value: bool | None):
        if value is None:
            return queryset
        queryset = self._live(queryset)
        return queryset.filter(live_online=True) if value else queryset.exclude(live_online=True)

    def filter_q(self, queryset, name, value: str):
        return queryset.filter(
            Q(name__icontains=value) | Q(java_host__icontains=value) | Q(summary__icontains=value)
        )

    def filter_sort(self, queryset, name, value: str):
        if value == "online":
            queryset = self._live(queryset)
        return queryset.order_by(*SORTS[value])
