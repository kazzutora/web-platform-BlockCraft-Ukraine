from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer

from .models import Skin
from .mojang import NICKNAME
from .styles import MAX_STYLES, Style


class SkinCardSerializer(serializers.ModelSerializer):
    """Catalog card: the 2D preview (the texture until it is rendered), title, counters."""

    author = UserBriefSerializer(read_only=True)
    texture_url = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()
    # Viewer state from social.selectors.with_viewer_state (false for guests)
    is_favorited = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Skin
        fields = [
            "id",
            "title",
            "author",
            "model",
            "texture_url",
            "preview_url",
            "dominant_color",
            "color_bucket",
            "style_tags",
            "likes_count",
            "favorites_count",
            "downloads_count",
            "is_favorited",
            "is_liked",
        ]
        read_only_fields = fields

    def get_texture_url(self, skin: Skin) -> str:
        return skin.file.url

    def get_preview_url(self, skin: Skin) -> str | None:
        return skin.preview.url if skin.preview else None

    def get_is_favorited(self, skin: Skin) -> bool:
        return bool(getattr(skin, "is_favorited", False))

    def get_is_liked(self, skin: Skin) -> bool:
        return bool(getattr(skin, "is_liked", False))


class SkinDetailSerializer(SkinCardSerializer):
    is_mine = serializers.SerializerMethodField()

    class Meta(SkinCardSerializer.Meta):
        fields = [
            *SkinCardSerializer.Meta.fields,
            "status",
            "rejection_reason",
            "is_current",
            "is_mine",
            "comments_count",
            "created_at",
            "published_at",
        ]
        read_only_fields = fields

    def get_is_mine(self, skin: Skin) -> bool:
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and skin.author_id == request.user.pk)


class StyleTagsField(serializers.ListField):
    child = serializers.ChoiceField(choices=Style.choices)
    max_length = MAX_STYLES


class SkinUploadSerializer(serializers.Serializer):
    file = serializers.FileField(help_text="PNG 64×64 or 64×32, up to 100 KB.")
    title = serializers.CharField(max_length=60)
    style_tags = StyleTagsField(required=False, default=list)
    model = serializers.ChoiceField(
        choices=Skin.Model.choices,
        required=False,
        allow_blank=True,
        default="",
        help_text="Empty: detected from the texture.",
    )


class SkinUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=60, required=False)
    style_tags = StyleTagsField(required=False)
    model = serializers.ChoiceField(choices=Skin.Model.choices, required=False)


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


class CurrentSkinSerializer(serializers.Serializer):
    skin_id = serializers.IntegerField()
