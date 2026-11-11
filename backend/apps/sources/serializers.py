from rest_framework import serializers

from apps.core.game import Loader
from apps.mods.serializers import CategorySerializer

from .models import GameVersion, SyncRun

UNSUPPORTED_VERSION = "Цієї версії гри немає серед підтримуваних."


class GameVersionField(serializers.PrimaryKeyRelatedField):
    """A supported Minecraft version for a foreign key; "" and null both mean «not chosen»."""

    default_error_messages = {
        **serializers.PrimaryKeyRelatedField.default_error_messages,
        "does_not_exist": UNSUPPORTED_VERSION,
    }

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("queryset", GameVersion.objects.supported())
        kwargs.setdefault("allow_null", True)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if data == "" and self.allow_null:
            return None
        return super().to_internal_value(data)


def validate_supported_version(value: str) -> str:
    """For models that keep the version as a string (packs)."""
    if not GameVersion.objects.supported().filter(pk=value).exists():
        raise serializers.ValidationError(UNSUPPORTED_VERSION)
    return value


class GameVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GameVersion
        fields = ["version", "version_type", "released_at", "is_major"]


class ServerCategorySerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    header = serializers.CharField()
    header_name = serializers.CharField()


class MetaSerializer(serializers.Serializer):
    game_versions = GameVersionSerializer(many=True, help_text="Supported, newest first.")
    loaders = serializers.ListField(child=serializers.ChoiceField(choices=Loader.choices))
    categories = CategorySerializer(many=True)
    server_languages = serializers.ListField(
        child=serializers.CharField(), help_text="ISO 639-1 codes of listed servers."
    )
    server_countries = serializers.ListField(
        child=serializers.CharField(), help_text="ISO 3166-1 alpha-2 codes of listed servers."
    )
    server_categories = ServerCategorySerializer(many=True)
    server_default_language = serializers.CharField(
        allow_blank=True, help_text="«uk» while there are at least 5 such servers, else empty."
    )


class RunSummarySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=SyncRun.Status.choices)
    started_at = serializers.DateTimeField()
    finished_at = serializers.DateTimeField(allow_null=True)
    created = serializers.IntegerField()
    updated = serializers.IntegerField()
    unchanged = serializers.IntegerField()
    skipped = serializers.IntegerField()
    failed = serializers.IntegerField()


class SourceJobSerializer(serializers.Serializer):
    key = serializers.CharField()
    title = serializers.CharField()
    last_run = RunSummarySerializer(allow_null=True)


class SourceSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    url = serializers.URLField()
    terms_url = serializers.CharField(allow_blank=True)
    last_sync = RunSummarySerializer(allow_null=True, help_text="The latest run of any job.")
    jobs = SourceJobSerializer(many=True)
