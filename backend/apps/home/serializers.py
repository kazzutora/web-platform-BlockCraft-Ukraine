from rest_framework import serializers

from apps.mods.serializers import ProjectCardSerializer
from apps.packs.serializers import PackCardSerializer
from apps.servers.serializers import ServerCardSerializer
from apps.skins.serializers import SkinCardSerializer


class ForYouSerializer(serializers.Serializer):
    basis = serializers.ChoiceField(
        choices=["profile", "popular"],
        help_text="`profile`: for the player's version and loader; `popular`: this week's best.",
    )
    game_version = serializers.CharField(allow_blank=True)
    loader = serializers.CharField(allow_blank=True)
    mods = ProjectCardSerializer(many=True)


class HomeSerializer(serializers.Serializer):
    for_you = ForYouSerializer()
    packs = PackCardSerializer(many=True)
    skin_of_week = SkinCardSerializer(allow_null=True)
    servers_online = ServerCardSerializer(many=True)
    new_skins = SkinCardSerializer(many=True)
    new_servers = ServerCardSerializer(many=True)


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
