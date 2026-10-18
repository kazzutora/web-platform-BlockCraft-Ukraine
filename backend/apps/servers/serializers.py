from urllib.parse import urlparse

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer

from .choices import MAX_MODES, Edition, Language, Mode
from .models import Server

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
    """Catalog row: name, modes, address and live online from Redis (context `live`)."""

    address = serializers.CharField(read_only=True)
    banner_url = serializers.SerializerMethodField()
    live = serializers.SerializerMethodField()
    # Viewer state from social.selectors.with_viewer_state (false/null for guests)
    is_favorited = serializers.SerializerMethodField()
    my_review_stars = serializers.SerializerMethodField()

    class Meta:
        model = Server
        fields = [
            "slug",
            "name",
            "address",
            "edition",
            "modes",
            "versions_label",
            "language",
            "has_whitelist",
            "is_verified",
            "banner_url",
            "rating_avg",
            "rating_count",
            "favorites_count",
            "is_favorited",
            "my_review_stars",
            "live",
        ]
        read_only_fields = fields

    def get_banner_url(self, server: Server) -> str | None:
        return server.banner.url if server.banner else None

    @extend_schema_field(LiveStatusSerializer(allow_null=True))
    def get_live(self, server: Server) -> dict | None:
        live = self.context.get("live", {}).get(server.pk)
        return LiveStatusSerializer(live).data if live else None

    def get_is_favorited(self, server: Server) -> bool:
        return bool(getattr(server, "is_favorited", False))

    def get_my_review_stars(self, server: Server) -> int | None:
        return getattr(server, "my_review_stars", None)


class ServerDetailSerializer(ServerCardSerializer):
    author = UserBriefSerializer(read_only=True)
    is_mine = serializers.SerializerMethodField()
    verify_code = serializers.SerializerMethodField()

    class Meta(ServerCardSerializer.Meta):
        fields = [
            *ServerCardSerializer.Meta.fields,
            "host",
            "port",
            "description",
            "discord_url",
            "website_url",
            "author",
            "comments_count",
            "ip_copies_count",
            "last_online_at",
            "status",
            "rejection_reason",
            "is_mine",
            "verify_code",
            "created_at",
        ]
        read_only_fields = fields

    def _is_mine(self, server: Server) -> bool:
        request = self.context.get("request")
        return bool(
            request and request.user.is_authenticated and server.author_id == request.user.pk
        )

    def get_is_mine(self, server: Server) -> bool:
        return self._is_mine(server)

    def get_verify_code(self, server: Server) -> str | None:
        """Only the owner sees the code for the MOTD."""
        return server.verify_code if self._is_mine(server) and not server.is_verified else None


class ServerWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=60)
    host = serializers.CharField(max_length=260, help_text="play.example.com, an IP or host:port")
    port = serializers.IntegerField(
        required=False, allow_null=True, help_text="Empty: 25565 (Java) or 19132 (Bedrock)."
    )
    edition = serializers.ChoiceField(choices=Edition.choices)
    modes = serializers.ListField(
        child=serializers.ChoiceField(choices=Mode.choices), min_length=1, max_length=MAX_MODES
    )
    versions_label = serializers.CharField(max_length=32, required=False, allow_blank=True)
    language = serializers.ChoiceField(choices=Language.choices)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    discord_url = serializers.URLField(required=False, allow_blank=True)
    website_url = serializers.URLField(required=False, allow_blank=True)
    has_whitelist = serializers.BooleanField(required=False, default=False)

    def validate_discord_url(self, value: str) -> str:
        if value and urlparse(value).hostname not in DISCORD_HOSTS:
            raise serializers.ValidationError("Посилання має вести на discord.gg або discord.com.")
        return value


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


class BannerUploadSerializer(serializers.Serializer):
    banner = serializers.FileField(help_text="PNG, JPEG or WebP up to 2 MB; cropped to 1200×300.")


class IpCopiesSerializer(serializers.Serializer):
    ip_copies_count = serializers.IntegerField()
