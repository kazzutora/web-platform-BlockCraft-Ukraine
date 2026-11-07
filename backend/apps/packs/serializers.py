from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer
from apps.mods.models import Project, ProjectVersion
from apps.sources.serializers import validate_supported_version

from . import selectors
from .choices import MAX_STYLES, PackLoader, Style
from .models import Pack, PackItem


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
    class Meta:
        model = ProjectVersion
        fields = ["id", "version_number", "file_name", "file_size", "game_versions", "loaders"]
        read_only_fields = fields


class PackItemSerializer(serializers.ModelSerializer):
    project = PackProjectSerializer(read_only=True)
    version = PackFileSerializer(read_only=True, allow_null=True)

    class Meta:
        model = PackItem
        fields = ["project", "version", "is_required", "added_as_dependency"]
        read_only_fields = fields


class IssueSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["no_version", "missing_dependency", "conflict"])
    project = PackIconSerializer()
    other = PackIconSerializer(allow_null=True)
    other_modrinth_id = serializers.CharField(allow_blank=True)
    message = serializers.CharField()


class PackBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pack
        fields = ["slug", "title"]
        read_only_fields = fields


class PackCardSerializer(serializers.ModelSerializer):
    """Catalog card: cover (or the first mod icons), target and counters."""

    author = UserBriefSerializer(read_only=True)
    cover_url = serializers.SerializerMethodField()
    mods_count = serializers.IntegerField(read_only=True)
    icons = serializers.SerializerMethodField()
    # Viewer state from social.selectors.with_viewer_state (false/null for guests)
    is_favorited = serializers.SerializerMethodField()
    my_review_stars = serializers.SerializerMethodField()

    class Meta:
        model = Pack
        fields = [
            "slug",
            "title",
            "summary",
            "author",
            "cover_url",
            "icons",
            "style_tags",
            "game_version",
            "loader",
            "is_official",
            "mods_count",
            "rating_avg",
            "rating_count",
            "favorites_count",
            "downloads_count",
            "modrinth_downloads",
            "is_favorited",
            "my_review_stars",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.CharField(allow_null=True))
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
                key=lambda item: (item.added_as_dependency, item.position, item.pk),
            )[: selectors.PREVIEW_ICONS]
        return PackIconSerializer([item.project for item in items], many=True).data

    def get_is_favorited(self, pack: Pack) -> bool:
        return bool(getattr(pack, "is_favorited", False))

    def get_my_review_stars(self, pack: Pack) -> int | None:
        return getattr(pack, "my_review_stars", None)


class PackDetailSerializer(PackCardSerializer):
    forked_from = PackBriefSerializer(read_only=True, allow_null=True)
    items = serializers.SerializerMethodField()
    issues = serializers.SerializerMethodField()
    effective_loader_version = serializers.SerializerMethodField()
    total_size = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()
    modrinth_url = serializers.SerializerMethodField()

    class Meta(PackCardSerializer.Meta):
        fields = [
            *PackCardSerializer.Meta.fields,
            "loader_version",
            "effective_loader_version",
            "ram_min_gb",
            "gpu_note",
            "install_md",
            "install_html",
            "changelog_md",
            "changelog_html",
            "forked_from",
            "forks_count",
            "items",
            "issues",
            "total_size",
            "status",
            "rejection_reason",
            "is_mine",
            "modrinth_url",
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
        return PackItemSerializer(self._items(pack), many=True).data

    @extend_schema_field(IssueSerializer(many=True))
    def get_issues(self, pack: Pack) -> list[dict]:
        return IssueSerializer(selectors.inspect(pack, self._items(pack)), many=True).data

    def get_effective_loader_version(self, pack: Pack) -> str:
        """What the .mrpack will ask for: pinned by the author or the latest stable build."""
        return selectors.loader_version(pack)

    def get_total_size(self, pack: Pack) -> int:
        return sum(item.version.file_size for item in self._items(pack) if item.version)

    def get_is_mine(self, pack: Pack) -> bool:
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and pack.author_id == request.user.pk)

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_modrinth_url(self, pack: Pack) -> str | None:
        return f"https://modrinth.com/modpack/{pack.modrinth_id}" if pack.modrinth_id else None


class PackWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=80)
    summary = serializers.CharField(max_length=280, required=False, allow_blank=True)
    style_tags = serializers.ListField(
        child=serializers.ChoiceField(choices=Style.choices),
        required=False,
        max_length=MAX_STYLES,
    )
    game_version = serializers.CharField(max_length=32, validators=[validate_supported_version])
    loader = serializers.ChoiceField(choices=PackLoader.choices)
    loader_version = serializers.CharField(
        max_length=64,
        required=False,
        allow_blank=True,
        help_text="Empty: the latest stable build at export time.",
    )
    ram_min_gb = serializers.IntegerField(min_value=1, max_value=64, required=False)
    gpu_note = serializers.CharField(max_length=140, required=False, allow_blank=True)
    install_md = serializers.CharField(max_length=5000, required=False, allow_blank=True)
    changelog_md = serializers.CharField(max_length=5000, required=False, allow_blank=True)

    def validate_loader_version(self, value: str) -> str:
        if value and not all(char.isalnum() or char in ".-+_" for char in value):
            raise serializers.ValidationError("Лише цифри, літери, крапки й дефіси.")
        return value


class PackItemAddSerializer(serializers.Serializer):
    project = serializers.SlugField(max_length=96, help_text="Slug of a catalog project.")


class PackItemUpdateSerializer(serializers.Serializer):
    is_required = serializers.BooleanField(
        help_text="Optional files are offered, not forced, by launchers."
    )


class CoverUploadSerializer(serializers.Serializer):
    cover = serializers.FileField(help_text="PNG, JPEG or WebP up to 2 MB; cropped to 1200×630.")


class MyPackSerializer(PackCardSerializer):
    """«Мої роботи»: drafts and the moderation outcome too."""

    class Meta(PackCardSerializer.Meta):
        fields = [*PackCardSerializer.Meta.fields, "status", "rejection_reason", "updated_at"]
        read_only_fields = fields
