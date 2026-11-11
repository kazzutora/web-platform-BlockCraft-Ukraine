import re

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.sources.attribution import SourceRef, SourceRefSerializer, source_ref

from . import selectors
from .models import Category, Project, ProjectVersion


class CategorySerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="name_uk")

    class Meta:
        model = Category
        fields = ["slug", "name", "project_type", "header"]


class ProjectCardSerializer(serializers.ModelSerializer):
    """Catalog card: one image, title, one line of metadata."""

    summary = serializers.SerializerMethodField()
    latest_game_version = serializers.SerializerMethodField()
    downloads = serializers.SerializerMethodField()
    categories = CategorySerializer(many=True, read_only=True)
    # Viewer state from social.selectors.with_viewer_state (false/null for guests)
    is_favorited = serializers.SerializerMethodField()
    my_review_stars = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()
    fits_my_game = serializers.SerializerMethodField(
        help_text="Has files for the viewer's «Моя гра»; null when nothing is chosen."
    )

    class Meta:
        model = Project
        fields = [
            "slug",
            "title",
            "summary",
            "project_type",
            "icon_url",
            "loaders",
            "latest_game_version",
            "categories",
            "downloads",
            "gpu_load",
            "rating_avg",
            "rating_count",
            "favorites_count",
            "is_favorited",
            "my_review_stars",
            "source",
            "fits_my_game",
        ]
        read_only_fields = fields

    @extend_schema_field(SourceRefSerializer)
    def get_source(self, project: Project) -> SourceRef:
        return source_ref(project.source, project.external_url)

    def get_fits_my_game(self, project: Project) -> bool | None:
        return selectors.fits_game(project, self.context.get("game"))

    def get_is_favorited(self, project: Project) -> bool:
        return bool(getattr(project, "is_favorited", False))

    def get_my_review_stars(self, project: Project) -> int | None:
        return getattr(project, "my_review_stars", None)

    def get_summary(self, project: Project) -> str:
        return project.summary_uk or project.summary

    def get_latest_game_version(self, project: Project) -> str:
        return selectors.latest_game_version(project)

    def get_downloads(self, project: Project) -> int:
        return project.modrinth_downloads + project.downloads_count


class GalleryImageSerializer(serializers.Serializer):
    url = serializers.URLField()
    title = serializers.CharField(allow_blank=True)
    featured = serializers.BooleanField()


class BylineSerializer(serializers.Serializer):
    """Who translated it («переклав @нік»); apps.accounts would import this module back."""

    nickname = serializers.CharField()


class ProjectDetailSerializer(ProjectCardSerializer):
    summary_uk_by = BylineSerializer(read_only=True, allow_null=True)
    body_uk_by = BylineSerializer(read_only=True, allow_null=True)
    summary_en = serializers.CharField(source="summary", read_only=True)
    gallery = GalleryImageSerializer(many=True, read_only=True)
    needs_translation = serializers.SerializerMethodField()
    updated_at = serializers.DateTimeField(source="modrinth_updated_at", read_only=True)

    class Meta(ProjectCardSerializer.Meta):
        fields = [
            "id",
            *ProjectCardSerializer.Meta.fields,
            "summary_en",
            "summary_uk",
            "summary_uk_by",
            "body_html",
            "body_uk_html",
            "body_uk_by",
            "gallery",
            "game_versions",
            "client_side",
            "server_side",
            "license",
            "source_url",
            "needs_translation",
            "published_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_needs_translation(self, project: Project) -> bool:
        return not project.summary_uk


class ProjectVersionSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="modrinth_version_id")

    class Meta:
        model = ProjectVersion
        fields = [
            "id",
            "name",
            "version_number",
            "version_type",
            "game_versions",
            "loaders",
            "file_name",
            "file_size",
            "date_published",
        ]
        read_only_fields = fields


class DependencyProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["slug", "title", "icon_url", "project_type"]
        read_only_fields = fields


class DependencySerializer(serializers.Serializer):
    project_id = serializers.CharField()
    dependency_type = serializers.ChoiceField(
        choices=["required", "optional", "incompatible", "embedded"]
    )
    project = DependencyProjectSerializer(allow_null=True)


class VersionsQuerySerializer(serializers.Serializer):
    game_version = serializers.CharField(required=False, allow_blank=True, max_length=32)
    loader = serializers.CharField(required=False, allow_blank=True, max_length=32)


class DownloadQuerySerializer(VersionsQuerySerializer):
    version = serializers.CharField(
        required=False, allow_blank=True, max_length=16, help_text="Exact Modrinth version id."
    )


class VersionsSerializer(serializers.Serializer):
    """What to install for the requested game version and loader."""

    game_version = serializers.CharField(allow_blank=True)
    loader = serializers.CharField(allow_blank=True)
    recommended = ProjectVersionSerializer(allow_null=True)
    dependencies = DependencySerializer(many=True)
    nearest_game_versions = serializers.ListField(child=serializers.CharField())
    versions = ProjectVersionSerializer(many=True)


class NoVersionErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()
    code = serializers.CharField()
    fields = serializers.DictField(child=serializers.ListField(child=serializers.CharField()))
    nearest_game_versions = serializers.ListField(child=serializers.CharField())


MODRINTH_URL = re.compile(
    r"^(?:https?://)?(?:www\.)?modrinth\.com/(?P<type>mod|resourcepack|shader|plugin|datapack|modpack|project)/(?P<slug>[\w.-]+)/?(?:[?#].*)?$",
    re.IGNORECASE,
)
SLUG = re.compile(r"^[\w.-]{2,96}$")


class ImportSerializer(serializers.Serializer):
    url = serializers.CharField(
        max_length=300, help_text="Link to the project on Modrinth or its slug."
    )

    def validate_url(self, value: str) -> str:
        """A link or slug → `sodium`; a modpack link → `modpack:<slug>`."""
        value = value.strip()
        match = MODRINTH_URL.match(value)
        slug = match.group("slug") if match else value
        if not SLUG.match(slug) or "/" in slug:
            raise serializers.ValidationError(
                "Встав посилання на сторінку проєкту Modrinth, наприклад https://modrinth.com/mod/sodium."
            )
        if match and match.group("type").lower() == "modpack":
            return f"modpack:{slug.lower()}"
        return slug.lower()


class ImportResponseSerializer(serializers.Serializer):
    job_id = serializers.UUIDField(allow_null=True, help_text="Poll GET /jobs/{id}; null if known.")
    slug = serializers.CharField(
        allow_blank=True, help_text="Set when the project is already here."
    )
    title = serializers.CharField(allow_blank=True)
