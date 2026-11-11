from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer
from apps.sources.attribution import SourceRef, SourceRefSerializer, source_ref

from .models import Skin
from .mojang import NICKNAME


class SkinCardSerializer(serializers.ModelSerializer):
    """Catalog card: the 2D preview (the texture until there is one), title, source."""

    texture_url = serializers.SerializerMethodField(help_text="Our cached 64×64 PNG.")
    preview_url = serializers.SerializerMethodField()
    # Viewer state from social.selectors.with_viewer_state (false for guests)
    is_favorited = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()

    class Meta:
        model = Skin
        fields = [
            "id",
            "title",
            "player_name",
            "model",
            "texture_url",
            "preview_url",
            "dominant_color",
            "color_bucket",
            "favorites_count",
            "downloads_count",
            "is_favorited",
            "source",
        ]
        read_only_fields = fields

    def get_texture_url(self, skin: Skin) -> str:
        return skin.texture.url

    def get_preview_url(self, skin: Skin) -> str | None:
        return skin.preview.url if skin.preview else None

    def get_is_favorited(self, skin: Skin) -> bool:
        return bool(getattr(skin, "is_favorited", False))

    @extend_schema_field(SourceRefSerializer)
    def get_source(self, skin: Skin) -> SourceRef:
        return source_ref(skin.source, skin.external_url or skin.texture_url)


class SkinDetailSerializer(SkinCardSerializer):
    added_by = UserBriefSerializer(read_only=True, allow_null=True)
    is_my_skin = serializers.SerializerMethodField(help_text="The viewer's «Мій скін».")

    class Meta(SkinCardSerializer.Meta):
        fields = [
            *SkinCardSerializer.Meta.fields,
            "added_by",
            "source_views",
            "is_my_skin",
            "created_at",
        ]
        read_only_fields = fields

    def get_is_my_skin(self, skin: Skin) -> bool:
        return self.context.get("my_skin_id") == skin.pk


class LookupQuerySerializer(serializers.Serializer):
    nickname = serializers.RegexField(
        NICKNAME,
        error_messages={"invalid": "Нік у Minecraft — 3–16 латинських літер, цифр або «_»."},
    )


class LookupResultSerializer(serializers.Serializer):
    nickname = serializers.CharField()
    uuid = serializers.CharField()
    model = serializers.ChoiceField(choices=Skin.Model.choices, allow_null=True)
    texture = serializers.CharField(
        allow_null=True, help_text="data:image/png;base64 URL; null for a default skin."
    )


class SkinAddSerializer(serializers.Serializer):
    """Either a Java nickname (Mojang) or a MineSkin link / UUID."""

    nickname = serializers.RegexField(
        NICKNAME,
        required=False,
        error_messages={"invalid": "Нік у Minecraft — 3–16 латинських літер, цифр або «_»."},
    )
    mineskin = serializers.CharField(
        required=False,
        max_length=200,
        error_messages={"blank": "Встав посилання на скін MineSkin або його UUID."},
    )

    def validate(self, attrs: dict) -> dict:
        if bool(attrs.get("nickname")) == bool(attrs.get("mineskin")):
            raise serializers.ValidationError("Вкажи нік або посилання MineSkin — щось одне.")
        return attrs


class SkinAddResultSerializer(serializers.Serializer):
    job_id = serializers.CharField(required=False, help_text="Poll GET /jobs/{id}.")
    id = serializers.IntegerField(required=False, help_text="Already in the catalog.")
    title = serializers.CharField(required=False)


class MySkinSerializer(serializers.Serializer):
    skin_id = serializers.IntegerField()
