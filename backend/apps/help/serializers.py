from rest_framework import serializers

from apps.compat.serializers import ResolutionSerializer, TargetSerializer
from apps.core.game import Loader
from apps.mods.serializers import ProjectCardSerializer
from apps.packs.choices import PackLoader

from .goals import GOALS


class CrashModSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=64, help_text="Mod id as the loader prints it.")
    name = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")


class CrashRequestSerializer(serializers.Serializer):
    """What the browser found in the log; the log itself is never sent."""

    mods = CrashModSerializer(many=True, max_length=100)
    game_version = serializers.CharField(max_length=32, required=False, allow_blank=True)
    loader = serializers.ChoiceField(choices=PackLoader.choices, required=False, allow_blank=True)


class CrashMatchSerializer(serializers.Serializer):
    id = serializers.CharField()
    project = ProjectCardSerializer(allow_null=True, help_text="null — not in our catalog.")


class LoaderReleaseSerializer(serializers.Serializer):
    loader = serializers.CharField()
    game_version = serializers.CharField()
    version = serializers.CharField()


class CrashResponseSerializer(serializers.Serializer):
    mods = CrashMatchSerializer(many=True)
    loader_release = LoaderReleaseSerializer(
        allow_null=True, help_text="The latest stable loader for the game of the log."
    )


class GoalsRequestSerializer(serializers.Serializer):
    goals = serializers.ListField(
        child=serializers.ChoiceField(choices=list(GOALS)), min_length=1, max_length=len(GOALS)
    )
    game_version = serializers.CharField(
        max_length=32, required=False, allow_blank=True, help_text="Defaults to «Моя гра»."
    )
    loader = serializers.ChoiceField(
        choices=Loader.choices,
        required=False,
        allow_blank=True,
        help_text="Defaults to «Моя гра»; `vanilla` is refused with `needs_mod_loader`.",
    )


class GoalChoiceSerializer(serializers.Serializer):
    slot = serializers.CharField()
    slug = serializers.CharField(allow_null=True, help_text="null — nothing fits the game.")


class GoalsPreviewSerializer(serializers.Serializer):
    target = TargetSerializer()
    choices = GoalChoiceSerializer(many=True)
    resolution = ResolutionSerializer()


class SavedPackSerializer(serializers.Serializer):
    slug = serializers.CharField()
