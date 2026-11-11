from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer
from apps.compat.serializers import HashedFileSerializer, ResolutionSerializer
from apps.core.game import GameContext
from apps.core.models import Source
from apps.mods.models import Project, ProjectVersion
from apps.sources.attribution import SourceRef, SourceRefSerializer, source_ref
from apps.sources.serializers import validate_supported_version

from . import selectors
from .choices import PackLoader
from .models import Pack, PackExternalFile, PackItem, Reason, Visibility


class PackProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["slug", "title", "icon_url", "project_type", "summary"]
        read_only_fields = fields


class PackIconSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["slug", "title", "icon_url"]
        read_only_fields = fields


class PackFileSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="modrinth_version_id")

    class Meta:
        model = ProjectVersion
        fields = ["id", "version_number", "file_name", "file_size", "game_versions", "loaders"]
        read_only_fields = fields


class PackItemSerializer(serializers.ModelSerializer):
    project = PackProjectSerializer(read_only=True)
    version = PackFileSerializer(read_only=True, allow_null=True)

    class Meta:
        model = PackItem
        fields = ["project", "version", "reason", "required_by", "env_client", "env_server"]
        read_only_fields = fields


class ExternalFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackExternalFile
        fields = ["path", "url", "size"]
        read_only_fields = fields


class PackBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pack
        fields = ["slug", "title"]
        read_only_fields = fields


class PackCardSerializer(serializers.ModelSerializer):
    """Catalog card: cover (or the first icons), target, compatibility and counters."""

    summary = serializers.SerializerMethodField(
        help_text="Ukrainian (an approved translation) when there is one."
    )
    author = UserBriefSerializer(read_only=True)
    cover_url = serializers.SerializerMethodField()
    icons = serializers.SerializerMethodField()
    # Viewer state from social.selectors.with_viewer_state (false/null for guests)
    is_favorited = serializers.SerializerMethodField()
    my_review_stars = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()
    fits_my_game = serializers.SerializerMethodField(
        help_text="Built for the viewer's «Моя гра»; null when nothing is chosen."
    )

    class Meta:
        model = Pack
        fields = [
            "slug",
            "title",
            "summary",
            "origin",
            "author",
            "cover_url",
            "icons",
            "game_version",
            "loader",
            "items_count",
            "compat_status",
            "rating_avg",
            "rating_count",
            "favorites_count",
            "downloads_count",
            "modrinth_downloads",
            "is_favorited",
            "my_review_stars",
            "source",
            "fits_my_game",
        ]
        read_only_fields = fields

    @extend_schema_field(SourceRefSerializer(allow_null=True))
    def get_source(self, pack: Pack) -> SourceRef | None:
        """Modpacks from Modrinth link back; community packs are made here."""
        if not pack.is_modrinth or not pack.external_url:
            return None
        return source_ref(Source.MODRINTH, pack.external_url)

    @extend_schema_field(serializers.CharField(allow_null=True))
    @extend_schema_field(serializers.CharField())
    @extend_schema_field(serializers.CharField())
    def get_summary(self, pack: Pack) -> str:
        return pack.summary_uk or pack.summary

    def get_cover_url(self, pack: Pack) -> str | None:
        if pack.cover:
            return pack.cover.url
        return pack.icon_url or None

    @extend_schema_field(PackIconSerializer(many=True))
    def get_icons(self, pack: Pack) -> list[dict]:
        items = getattr(pack, "preview_items", None)
        if items is None:
            items = sorted(
                getattr(pack, "all_items", []),
                key=lambda item: (item.reason != Reason.REQUESTED, item.position, item.pk),
            )[: selectors.PREVIEW_ICONS]
        return PackIconSerializer([item.project for item in items], many=True).data

    def get_is_favorited(self, pack: Pack) -> bool:
        return bool(getattr(pack, "is_favorited", False))

    def get_my_review_stars(self, pack: Pack) -> int | None:
        return getattr(pack, "my_review_stars", None)

    def get_fits_my_game(self, pack: Pack) -> bool | None:
        game: GameContext | None = self.context.get("game")
        if game is None or not game.is_set:
            return None
        return (not game.game_version or game.game_version == pack.game_version) and (
            not game.loader or game.loader == pack.loader
        )


class PackDetailSerializer(PackCardSerializer):
    summary_uk_by = UserBriefSerializer(read_only=True, allow_null=True)
    body_uk_by = UserBriefSerializer(read_only=True, allow_null=True)
    forked_from = PackBriefSerializer(read_only=True, allow_null=True)
    items = serializers.SerializerMethodField()
    external_files = ExternalFileSerializer(many=True, read_only=True)
    compat = serializers.SerializerMethodField(
        help_text="The last check of the set (`Resolution`); null before the first one."
    )
    effective_loader_version = serializers.SerializerMethodField()
    total_size = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()
    share_token = serializers.SerializerMethodField(
        help_text="Only for the author: `?share_token=` opens a «за посиланням» pack."
    )

    class Meta(PackCardSerializer.Meta):
        fields = [
            *PackCardSerializer.Meta.fields,
            "description_html",
            "summary_uk",
            "summary_uk_by",
            "body_uk_html",
            "body_uk_by",
            "notes_md",
            "notes_html",
            "loader_version",
            "effective_loader_version",
            "ram_min_gb",
            "forked_from",
            "forks_count",
            "items",
            "external_files",
            "compat",
            "compat_checked_at",
            "total_size",
            "status",
            "visibility",
            "share_token",
            "rejection_reason",
            "is_mine",
            "source_file_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def _items(self, pack: Pack) -> list[PackItem]:
        if hasattr(pack, "all_items"):
            return pack.all_items
        return list(pack.items.select_related("project", "version"))

    @extend_schema_field(PackItemSerializer(many=True))
    def get_items(self, pack: Pack) -> list[dict]:
        items = sorted(
            self._items(pack), key=lambda item: (item.reason != Reason.REQUESTED, item.position)
        )
        return PackItemSerializer(items, many=True).data

    @extend_schema_field(ResolutionSerializer(allow_null=True))
    def get_compat(self, pack: Pack) -> dict | None:
        return pack.compat_report or None

    def get_effective_loader_version(self, pack: Pack) -> str:
        """What the .mrpack will ask for: pinned by the author or the latest stable build."""
        return selectors.loader_version(pack)

    def get_total_size(self, pack: Pack) -> int:
        return sum(item.version.file_size for item in self._items(pack) if item.version)

    def get_is_mine(self, pack: Pack) -> bool:
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and pack.author_id == request.user.pk)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_share_token(self, pack: Pack) -> str | None:
        return pack.share_token if self.get_is_mine(pack) else None


class PackWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=80)
    summary = serializers.CharField(max_length=280, required=False, allow_blank=True)
    game_version = serializers.CharField(max_length=32, validators=[validate_supported_version])
    loader = serializers.ChoiceField(choices=PackLoader.choices)
    loader_version = serializers.CharField(
        max_length=64,
        required=False,
        allow_blank=True,
        help_text="Empty: the latest stable build at export time.",
    )
    ram_min_gb = serializers.IntegerField(min_value=1, max_value=64, required=False)
    notes_md = serializers.CharField(max_length=5000, required=False, allow_blank=True)
    visibility = serializers.ChoiceField(choices=Visibility.choices, required=False)

    def validate_loader_version(self, value: str) -> str:
        if value and not all(char.isalnum() or char in ".-+_" for char in value):
            raise serializers.ValidationError("Лише цифри, літери, крапки й дефіси.")
        return value


class PackItemAddSerializer(serializers.Serializer):
    project = serializers.SlugField(max_length=96, help_text="Slug of a catalog project.")


class PackItemUpdateSerializer(serializers.Serializer):
    optional = serializers.BooleanField(
        help_text="Launchers offer an optional file instead of installing it."
    )


class PublishSerializer(serializers.Serializer):
    visibility = serializers.ChoiceField(
        choices=[Visibility.PUBLIC, Visibility.LINK], default=Visibility.PUBLIC
    )


class TargetQuerySerializer(serializers.Serializer):
    game_version = serializers.CharField(max_length=32, validators=[validate_supported_version])
    loader = serializers.ChoiceField(choices=PackLoader.choices)


class ForkSerializer(serializers.Serializer):
    game_version = serializers.CharField(
        max_length=32, required=False, validators=[validate_supported_version]
    )
    loader = serializers.ChoiceField(choices=PackLoader.choices, required=False)


class ChangedSerializer(serializers.Serializer):
    project = serializers.CharField(help_text="Slug.")
    old_version = serializers.CharField(allow_null=True)
    new_version = serializers.CharField()


class RetargetSerializer(serializers.Serializer):
    target = serializers.DictField(child=serializers.CharField())
    kept = serializers.ListField(child=serializers.CharField())
    changed = ChangedSerializer(many=True)
    dropped = serializers.ListField(child=serializers.CharField())
    added = serializers.ListField(child=serializers.CharField())
    titles = serializers.DictField(child=serializers.CharField(), help_text="Slug → title.")


class PackFileLinkSerializer(serializers.Serializer):
    """«Встановити вручну»: one direct link per file, with the folder it goes to."""

    project = PackIconSerializer()
    file_name = serializers.CharField()
    url = serializers.URLField()
    size = serializers.IntegerField()
    folder = serializers.ChoiceField(
        choices=["mods", "resourcepacks", "shaderpacks", "datapacks"],
        help_text="datapacks: into a world's folder, not the game's.",
    )
    optional = serializers.BooleanField()


class MyPackSerializer(PackCardSerializer):
    """«Мої збірки»: drafts and private ones too."""

    class Meta(PackCardSerializer.Meta):
        fields = [*PackCardSerializer.Meta.fields, "status", "visibility", "updated_at"]
        read_only_fields = fields


class PackImportSerializer(serializers.Serializer):
    """`files` from a `mods` folder, or `index` — modrinth.index.json the browser took out
    of a .mrpack. Nothing else of the player's files reaches us."""

    title = serializers.CharField(max_length=80, required=False, allow_blank=True)
    game_version = serializers.CharField(
        max_length=32, required=False, allow_blank=True, help_text="Default: the guess."
    )
    loader = serializers.ChoiceField(choices=PackLoader.choices, required=False, allow_blank=True)
    files = HashedFileSerializer(many=True, required=False, max_length=2000)
    index = serializers.JSONField(required=False)

    def validate(self, attrs: dict) -> dict:
        if not attrs.get("files") and attrs.get("index") is None:
            raise serializers.ValidationError("Передай files або index.")
        index = attrs.get("index")
        if index is not None and (not isinstance(index, dict) or len(str(index)) > 2_000_000):
            raise serializers.ValidationError({"index": "Це не modrinth.index.json."})
        return attrs
