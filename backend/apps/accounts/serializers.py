import re

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.core.game import GAME_VERSIONS, Edition, Loader

from .models import GameProfile, Interest, User, UserSettings

MC_NICKNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,16}$")


def avatar_url(user: User) -> str | None:
    return user.avatar.url if user.avatar else None


class GameProfileSerializer(serializers.ModelSerializer):
    interests = serializers.ListField(
        child=serializers.ChoiceField(choices=Interest.choices), required=False, max_length=8
    )

    class Meta:
        model = GameProfile
        fields = ["game_version", "loader", "edition", "interests", "onboarding_done"]
        read_only_fields = ["onboarding_done"]


class OnboardingSerializer(serializers.Serializer):
    """Everything is optional: the player may skip onboarding."""

    game_version = serializers.ChoiceField(choices=GAME_VERSIONS, required=False, allow_blank=True)
    loader = serializers.ChoiceField(choices=Loader.choices, required=False, allow_blank=True)
    edition = serializers.ChoiceField(choices=Edition.choices, required=False)
    interests = serializers.ListField(
        child=serializers.ChoiceField(choices=Interest.choices), required=False, max_length=8
    )


class MeSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    game_profile = GameProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "nickname",
            "avatar_url",
            "bio",
            "mc_nickname",
            "role",
            "level",
            "xp",
            "is_private",
            "published_count",
            "date_joined",
            "game_profile",
        ]
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.STR)
    def get_avatar_url(self, user: User) -> str | None:
        return avatar_url(user)


class MeUpdateSerializer(serializers.ModelSerializer):
    mc_nickname = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, max_length=16
    )

    class Meta:
        model = User
        fields = ["bio", "mc_nickname", "is_private"]

    def validate_mc_nickname(self, value: str | None) -> str:
        if not value:
            return ""
        if not MC_NICKNAME_RE.match(value):
            raise serializers.ValidationError(
                "Нік у Minecraft: 3–16 символів, латиниця, цифри та «_»."
            )
        return value


class AvatarUploadSerializer(serializers.Serializer):
    avatar = serializers.FileField()


class UserSettingsSerializer(serializers.ModelSerializer):
    notify_prefs = serializers.DictField(child=serializers.BooleanField(), required=False)

    class Meta:
        model = UserSettings
        fields = [
            "theme",
            "language",
            "notify_prefs",
            "history_enabled",
            "who_can_comment",
            "collections_visible",
        ]


class PublicProfileSerializer(serializers.Serializer):
    """For closed profiles everything except the nickname is null."""

    nickname = serializers.CharField()
    is_private = serializers.BooleanField()
    avatar_url = serializers.CharField(allow_null=True)
    bio = serializers.CharField(allow_null=True)
    mc_nickname = serializers.CharField(allow_null=True)
    level = serializers.IntegerField(allow_null=True)
    date_joined = serializers.DateTimeField(allow_null=True)

    @classmethod
    def from_user(cls, user: User, *, full: bool) -> "PublicProfileSerializer":
        data = {
            "nickname": user.nickname,
            "is_private": user.is_private,
            "avatar_url": avatar_url(user) if full else None,
            "bio": user.bio if full else None,
            "mc_nickname": user.mc_nickname if full else None,
            "level": user.level if full else None,
            "date_joined": user.date_joined if full else None,
        }
        return cls(data)
