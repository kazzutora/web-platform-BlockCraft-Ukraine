import re

from rest_framework import serializers

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
        ]
        read_only_fields = fields

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


class ProjectDetailSerializer(ProjectCardSerializer):
    summary_en = serializers.CharField(source="summary", read_only=True)
    gallery = GalleryImageSerializer(many=True, read_only=True)
    modrinth_url = serializers.CharField(read_only=True)
    needs_translation = serializers.SerializerMethodField()
    updated_at = serializers.DateTimeField(source="modrinth_updated_at", read_only=True)

    class Meta(ProjectCardSerializer.Meta):
        fields = [
            "id",
            *ProjectCardSerializer.Meta.fields,
            "summary_en",
            "summary_uk",
            "body_html",
            "gallery",
            "game_versions",
            "license",
            "source_url",
            "modrinth_url",
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
            "released_at",
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
    r"^(?:https?://)?(?:www\.)?modrinth\.com/(?:mod|resourcepack|shader|plugin|datapack|modpack|project)/(?P<slug>[\w.-]+)/?(?:[?#].*)?$",
    re.IGNORECASE,
)
SLUG = re.compile(r"^[\w.-]{2,96}$")


class SuggestSerializer(serializers.Serializer):
    url = serializers.CharField(
        max_length=300, help_text="Link to the project on Modrinth or its slug."
    )

    def validate_url(self, value: str) -> str:
        value = value.strip()
        match = MODRINTH_URL.match(value)
        slug = match.group("slug") if match else value
        if not SLUG.match(slug) or "/" in slug:
            raise serializers.ValidationError(
                "Встав посилання на сторінку проєкту Modrinth, наприклад https://modrinth.com/mod/sodium."
            )
        return slug.lower()


class SuggestResponseSerializer(serializers.Serializer):
    slug = serializers.CharField()
    status = serializers.ChoiceField(choices=["queued", "exists"])
