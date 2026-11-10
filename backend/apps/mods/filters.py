import django_filters
from django.db.models import Q, QuerySet

from apps.core.game import GameContext, Loader, game_context

from . import selectors
from .models import Project, ProjectType

SORTS = {
    "popular": ["-modrinth_downloads"],
    "new": ["-published_at"],
    "updated": ["-modrinth_updated_at"],
    "top": ["-score", "-modrinth_downloads"],
    "trend": ["-trend_score", "-modrinth_downloads"],
}


class ProjectFilter(django_filters.FilterSet):
    """Catalog filters. Without `game_version` / `loader` the viewer's «Моя гра» applies;
    `all=1` turns the game filter off (tech.md 7, 10.2)."""

    type = django_filters.ChoiceFilter(
        method="filter_type",
        choices=ProjectType.choices,
        help_text="Datapacks include mods that also ship as a datapack.",
    )
    game_version = django_filters.CharFilter(
        method="filter_noop", help_text="Defaults to «Моя гра» of the viewer."
    )
    loader = django_filters.ChoiceFilter(
        method="filter_noop",
        choices=Loader.choices,
        help_text="Applies to mods; defaults to «Моя гра». Vanilla keeps mods with a datapack.",
    )
    all = django_filters.BooleanFilter(
        method="filter_noop", help_text="1 — ignore «Моя гра» and show every version."
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
        fields = ["type", "game_version", "loader", "all", "category", "gpu_load", "q", "sort"]

    def game(self) -> GameContext:
        """The game the catalog is filtered for: query parameters, else «Моя гра»."""
        data = self.form.cleaned_data
        if self.shows_all() or self.request is None:
            mine = GameContext()
        else:
            mine = game_context(self.request)

        def pick(name: str, default: str) -> str:
            # A parameter present in the query wins, even empty ("any version")
            return (data.get(name) or "") if name in self.data else default

        return GameContext(
            pick("game_version", mine.game_version), pick("loader", mine.loader), "query"
        )

    def shows_all(self) -> bool:
        # `all=1` in the URL (tech.md 7); the boolean widget alone only knows "true"
        return str(self.data.get("all", "")).lower() in {"1", "true"}

    @property
    def qs(self) -> QuerySet[Project]:
        queryset = super().qs
        game = self.game()
        if game.game_version:
            queryset = queryset.filter(game_versions__contains=[game.game_version])
        queryset = queryset.filter(selectors.for_loader(game.loader))
        if not self.form.cleaned_data.get("sort"):
            queryset = queryset.order_by(*SORTS["popular"])
        return queryset

    def filter_noop(self, queryset, name, value):
        # Applied together in `qs`: defaults depend on which of them came in the query
        return queryset

    def filter_type(self, queryset, name, value: str):
        return queryset.filter(selectors.of_type(value))

    def filter_category(self, queryset, name, value: str):
        for slug in filter(None, (part.strip() for part in value.split(","))):
            queryset = queryset.filter(categories__slug=slug)
        return queryset.distinct()

    def filter_q(self, queryset, name, value: str):
        # Plain search; the search box uses Meilisearch (R8)
        return queryset.filter(
            Q(title__icontains=value) | Q(summary__icontains=value) | Q(summary_uk__icontains=value)
        )

    def filter_sort(self, queryset, name, value: str):
        return queryset.order_by(*SORTS[value])
