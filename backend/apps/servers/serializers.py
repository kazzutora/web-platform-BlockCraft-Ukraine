from urllib.parse import urlparse

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer
from apps.core.models import Source
from apps.packs.serializers import PackCardSerializer
from apps.sources.attribution import SourceRef, SourceRefSerializer, source_ref

from . import selectors
from .models import ContentKind, Server
from .services import claim_code

DISCORD_HOSTS = {"discord.gg", "discord.com", "www.discord.com", "discordapp.com"}


class LiveStatusSerializer(serializers.Serializer):
    """Result of the latest ping (every 5 minutes); null when there is none yet."""

    is_online = serializers.BooleanField()
    players_online = serializers.IntegerField()
    players_max = serializers.IntegerField()
    latency_ms = serializers.IntegerField(allow_null=True)
    version_name = serializers.CharField(allow_blank=True)
    checked_at = serializers.DateTimeField()


class ServerCardSerializer(serializers.ModelSerializer):
    """Catalog row: name, address, what is needed to join and live online (context `live`)."""

    summary = serializers.SerializerMethodField(
        help_text="The owner's words, else the approved translation, else Modrinth's."
    )
    address = serializers.CharField(read_only=True)
    edition = serializers.CharField(read_only=True)
    live = serializers.SerializerMethodField()
    # Viewer state from social.selectors.with_viewer_state (false/null for guests)
    is_favorited = serializers.SerializerMethodField()
    my_review_stars = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()

    class Meta:
        model = Server
        fields = [
            "slug",
            "name",
            "summary",
            "address",
            "edition",
            "country",
            "languages",
            "categories",
            "content_kind",
            "supported_versions",
            "recommended_version",
            "icon_url",
            "banner_url",
            "is_verified",
            "modrinth_plays",
            "rating_avg",
            "rating_count",
            "favorites_count",
            "is_favorited",
            "my_review_stars",
            "live",
            "source",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.CharField())
    def get_summary(self, server: Server) -> str:
        if server.owner_id:
            return server.summary
        return server.summary_uk or server.summary

    @extend_schema_field(LiveStatusSerializer(allow_null=True))
    def get_live(self, server: Server) -> dict | None:
        live = self.context.get("live", {}).get(server.pk)
        return LiveStatusSerializer(live).data if live else None

    def get_is_favorited(self, server: Server) -> bool:
        return bool(getattr(server, "is_favorited", False))

    def get_my_review_stars(self, server: Server) -> int | None:
        return getattr(server, "my_review_stars", None)

    @extend_schema_field(SourceRefSerializer(allow_null=True))
    def get_source(self, server: Server) -> SourceRef | None:
        """Modrinth servers link back; a server added by its owner has only the owner."""
        if server.source != Source.MODRINTH:
            return None
        return source_ref(Source.MODRINTH, server.external_url)


class ServerDetailSerializer(ServerCardSerializer):
    summary_uk_by = UserBriefSerializer(read_only=True, allow_null=True)
    body_uk_by = UserBriefSerializer(read_only=True, allow_null=True)
    owner = UserBriefSerializer(read_only=True, allow_null=True)
    is_mine = serializers.SerializerMethodField(help_text="The viewer owns it (code proved).")
    is_claimed_by_me = serializers.SerializerMethodField(
        help_text="The viewer asked to own it and has to put the code into the MOTD."
    )
    verify_code = serializers.SerializerMethodField()
    required_pack = serializers.SerializerMethodField()

    class Meta(ServerCardSerializer.Meta):
        fields = [
            *ServerCardSerializer.Meta.fields,
            "java_host",
            "java_port",
            "bedrock_host",
            "bedrock_port",
            "description_html",
            "summary_uk",
            "summary_uk_by",
            "body_uk_html",
            "body_uk_by",
            "description_uk_md",
            "description_uk_html",
            "discord_url",
            "website_url",
            "required_pack",
            "owner",
            "ip_copies_count",
            "last_online_at",
            "is_mine",
            "is_claimed_by_me",
            "verify_code",
            "created_at",
        ]
        read_only_fields = fields

    def _viewer(self):
        request = self.context.get("request")
        return request.user if request and request.user.is_authenticated else None

    def get_is_mine(self, server: Server) -> bool:
        viewer = self._viewer()
        return bool(viewer and server.owner_id == viewer.pk)

    def get_is_claimed_by_me(self, server: Server) -> bool:
        viewer = self._viewer()
        return bool(viewer and server.claimant_id == viewer.pk)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_verify_code(self, server: Server) -> str | None:
        """Only whoever claims the server sees their own code for the MOTD."""
        viewer = self._viewer()
        if viewer is None or not self.get_is_claimed_by_me(server):
            return None
        return claim_code(server.pk, viewer.pk)

    @extend_schema_field(PackCardSerializer(allow_null=True))
    def get_required_pack(self, server: Server) -> dict | None:
        pack = selectors.pack_for_joining(server)
        if pack is None:
            return None
        return PackCardSerializer(pack, context=self.context).data


class ServerAddSerializer(serializers.Serializer):
    address = serializers.CharField(max_length=260, help_text="play.example.com, an IP, host:port")
    edition = serializers.ChoiceField(choices=["java", "bedrock"], default="java")


class ServerWriteSerializer(serializers.Serializer):
    """What an owner may change; name, languages… only for servers added here."""

    name = serializers.CharField(max_length=80, required=False)
    summary = serializers.CharField(max_length=280, required=False, allow_blank=True)
    description_uk_md = serializers.CharField(max_length=5000, required=False, allow_blank=True)
    discord_url = serializers.URLField(required=False, allow_blank=True)
    website_url = serializers.URLField(required=False, allow_blank=True)
    required_pack = serializers.CharField(
        max_length=96, required=False, allow_blank=True, help_text="Pack slug; empty clears."
    )
    languages = serializers.ListField(
        child=serializers.RegexField(r"^[a-z]{2}$"), required=False, max_length=10
    )
    country = serializers.RegexField(r"^[A-Za-z]{2}$|^$", required=False, allow_blank=True)
    categories = serializers.ListField(
        child=serializers.CharField(max_length=48), required=False, max_length=10
    )
    content_kind = serializers.ChoiceField(choices=ContentKind.choices, required=False)
    supported_versions = serializers.ListField(
        child=serializers.CharField(max_length=32), required=False, max_length=20
    )
    recommended_version = serializers.CharField(max_length=32, required=False, allow_blank=True)

    def validate_discord_url(self, value: str) -> str:
        if value and urlparse(value).hostname not in DISCORD_HOSTS:
            raise serializers.ValidationError("Посилання має вести на discord.gg або discord.com.")
        return value

    def validate_country(self, value: str) -> str:
        return value.upper()


class JoinSerializer(serializers.Serializer):
    """«Щоб зайти»: the address, and either a game version or a pack to take."""

    address = serializers.CharField()
    edition = serializers.CharField()
    kind = serializers.ChoiceField(choices=ContentKind.choices)
    versions = serializers.ListField(child=serializers.CharField())
    recommended_version = serializers.CharField(allow_blank=True)
    pack = PackCardSerializer(allow_null=True)
    pack_pending = serializers.BooleanField(
        help_text="Modded, and the pack is still being imported from Modrinth."
    )
    fits_my_game = serializers.BooleanField(
        allow_null=True, help_text="The viewer's «Моя гра» can join as it is; null — unknown."
    )


class StatsQuerySerializer(serializers.Serializer):
    range = serializers.ChoiceField(choices=["24h", "7d"], default="24h")


class StatsPointSerializer(serializers.Serializer):
    ts = serializers.DateTimeField()
    players = serializers.FloatField()
    is_online = serializers.BooleanField()


class StatsSerializer(serializers.Serializer):
    range = serializers.CharField()
    uptime_percent = serializers.FloatField(allow_null=True)
    peak_players = serializers.IntegerField()
    points = StatsPointSerializer(many=True)


class VerificationSerializer(serializers.Serializer):
    state = serializers.ChoiceField(choices=["idle", "checking", "verified", "missing", "offline"])


class IpCopiesSerializer(serializers.Serializer):
    ip_copies_count = serializers.IntegerField()
