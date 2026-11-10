import django_filters
from django.db.models import Q, QuerySet
from django.db.models.functions import Lower

from apps.core.game import GameContext, game_context

from .choices import PackLoader
from .models import Origin, Pack

SORTS = {
    "popular": ["-score", "-favorites_count", "-modrinth_downloads"],
    "new": ["-published_at"],
    "top": ["-score", "-rating_count"],
    "trend": ["-trend_score", "-score"],
    "downloads": ["-downloads_count", "-modrinth_downloads"],
}


class PackFilter(django_filters.FilterSet):
    """Without `game_version` / `loader` the viewer's «Моя гра» applies; `all=1` — none."""

    origin = django_filters.ChoiceFilter(choices=Origin.choices)
    game_version = django_filters.CharFilter(
        method="filter_noop", help_text="Defaults to «Моя гра» of the viewer."
    )
    loader = django_filters.ChoiceFilter(
        method="filter_noop", choices=PackLoader.choices, help_text="Defaults to «Моя гра»."
    )
    all = django_filters.BooleanFilter(method="filter_noop", help_text="1 — ignore «Моя гра».")
    author = django_filters.CharFilter(method="filter_author", help_text="Author nickname.")
    q = django_filters.CharFilter(method="filter_q")
    sort = django_filters.ChoiceFilter(
        method="filter_sort", choices=[(key, key) for key in SORTS], empty_label=None
    )

    class Meta:
        model = Pack
        fields = ["origin", "game_version", "loader", "all", "author", "q", "sort"]

    def game(self) -> GameContext:
        data = self.form.cleaned_data
        shows_all = str(self.data.get("all", "")).lower() in {"1", "true"}
        mine = GameContext() if shows_all or self.request is None else game_context(self.request)

        def pick(name: str, default: str) -> str:
            return (data.get(name) or "") if name in self.data else default

        # A vanilla game has no pack loader: packs for any loader of that version
        loader = pick("loader", mine.loader if mine.loader in PackLoader.values else "")
        return GameContext(pick("game_version", mine.game_version), loader, "query")

    @property
    def qs(self) -> QuerySet[Pack]:
        queryset = super().qs
        game = self.game()
        if game.game_version:
            queryset = queryset.filter(game_version=game.game_version)
        if game.loader:
            queryset = queryset.filter(loader=game.loader)
        if not self.form.cleaned_data.get("sort"):
            queryset = queryset.order_by(*SORTS["popular"])
        return queryset

    def filter_noop(self, queryset, name, value):
        return queryset

    def filter_author(self, queryset, name, value: str):
        return queryset.alias(owner_nickname=Lower("author__nickname")).filter(
            owner_nickname=value.lower()
        )

    def filter_q(self, queryset, name, value: str):
        return queryset.filter(Q(title__icontains=value) | Q(summary__icontains=value))

    def filter_sort(self, queryset, name, value: str):
        return queryset.order_by(*SORTS[value])
