import django_filters
from django.db.models import F, Q, QuerySet
from django.db.models.functions import Lower
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field

from . import selectors
from .choices import Edition, Language, Mode
from .models import Server

SORTS = {
    "popular": ["-score", "-favorites_count"],
    "online": [F("live_players").desc(nulls_last=True), "-score"],
    "new": ["-published_at"],
    "top": ["-score", "-rating_count"],
}


class ServerFilter(django_filters.FilterSet):
    mode = django_filters.CharFilter(
        method="filter_mode", help_text="Mode slugs, comma-separated; any may match."
    )
    edition = django_filters.ChoiceFilter(
        method="filter_edition",
        choices=Edition.choices,
        help_text="`java` and `bedrock` include servers for both.",
    )
    language = django_filters.ChoiceFilter(choices=Language.choices)
    version = django_filters.CharFilter(field_name="versions_label", lookup_expr="icontains")
    online = django_filters.BooleanFilter(method="filter_online", help_text="Online right now.")
    whitelist = django_filters.BooleanFilter(field_name="has_whitelist")
    author = django_filters.CharFilter(method="filter_author", help_text="Owner nickname.")
    q = django_filters.CharFilter(method="filter_q")
    sort = django_filters.ChoiceFilter(
        method="filter_sort", choices=[(key, key) for key in SORTS], empty_label=None
    )

    class Meta:
        model = Server
        fields = ["mode", "edition", "language", "version", "online", "whitelist", "q", "sort"]

    @property
    def qs(self) -> QuerySet[Server]:
        queryset = super().qs
        if not self.form.cleaned_data.get("sort"):
            queryset = queryset.order_by(*SORTS["popular"])
        return queryset

    def _live(self, queryset: QuerySet[Server]) -> QuerySet[Server]:
        return (
            queryset
            if "live_players" in queryset.query.annotations
            else selectors.with_live(queryset)
        )

    def filter_mode(self, queryset, name, value: str):
        modes = [part for part in (p.strip() for p in value.split(",")) if part in Mode.values]
        return queryset.filter(modes__overlap=modes) if modes else queryset

    def filter_edition(self, queryset, name, value: str):
        return queryset.filter(edition__in=[value, Edition.BOTH])

    @extend_schema_field(OpenApiTypes.BOOL)
    def filter_online(self, queryset, name, value: bool | None):
        if value is None:
            return queryset
        queryset = self._live(queryset)
        return queryset.filter(live_online=True) if value else queryset.exclude(live_online=True)

    def filter_author(self, queryset, name, value: str):
        return queryset.alias(owner_nickname=Lower("author__nickname")).filter(
            owner_nickname=value.lower()
        )

    def filter_q(self, queryset, name, value: str):
        return queryset.filter(
            Q(name__icontains=value) | Q(host__icontains=value) | Q(description__icontains=value)
        )

    def filter_sort(self, queryset, name, value: str):
        if value == "online":
            queryset = self._live(queryset)
        return queryset.order_by(*SORTS[value])
