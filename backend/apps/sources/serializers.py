from rest_framework import serializers

from apps.core.game import Loader
from apps.mods.serializers import CategorySerializer

from .models import GameVersion

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


class MetaSerializer(serializers.Serializer):
    game_versions = GameVersionSerializer(many=True, help_text="Supported, newest first.")
    loaders = serializers.ListField(child=serializers.ChoiceField(choices=Loader.choices))
    categories = CategorySerializer(many=True)
