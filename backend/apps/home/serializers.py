from rest_framework import serializers

from apps.mods.serializers import ProjectCardSerializer
from apps.packs.serializers import PackCardSerializer
from apps.servers.serializers import ServerCardSerializer
from apps.skins.serializers import SkinCardSerializer


class ForYouSerializer(serializers.Serializer):
    basis = serializers.ChoiceField(
        choices=["profile", "popular"],
        help_text="`profile`: for «Моя гра» (mods and packs fit it); `popular`: this week's best.",
    )
    game_version = serializers.CharField(allow_blank=True)
    loader = serializers.CharField(allow_blank=True)
    mods = ProjectCardSerializer(many=True)


class HomeSerializer(serializers.Serializer):
    for_you = ForYouSerializer()
    packs = PackCardSerializer(many=True, help_text="«Готові збірки»: for «Моя гра» when chosen.")
    servers_online = ServerCardSerializer(many=True, help_text="Ukrainian-speaking, online now.")
    skin_of_day = SkinCardSerializer(allow_null=True)
    skins = SkinCardSerializer(many=True, help_text="The newest, without the skin of the day.")


class TopQuerySerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["mod", "pack", "skin", "server"], default="mod")
    period = serializers.ChoiceField(choices=["week", "month", "all"], default="week")


class TopSerializer(serializers.Serializer):
    """Exactly one list is filled: the one of the requested kind."""

    kind = serializers.CharField()
    period = serializers.CharField()
    mods = ProjectCardSerializer(many=True)
    packs = PackCardSerializer(many=True)
    skins = SkinCardSerializer(many=True)
    servers = ServerCardSerializer(many=True)
