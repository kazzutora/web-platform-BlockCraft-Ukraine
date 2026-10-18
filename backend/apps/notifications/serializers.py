from rest_framework import serializers

from .models import Notification


class NotificationPayloadSerializer(serializers.Serializer):
    kind = serializers.CharField(required=False)
    id = serializers.CharField(required=False)
    title = serializers.CharField(required=False)
    reason = serializers.CharField(required=False)
    actor = serializers.CharField(required=False)
    excerpt = serializers.CharField(required=False)


class NotificationSerializer(serializers.ModelSerializer):
    payload = NotificationPayloadSerializer()

    class Meta:
        model = Notification
        fields = ["id", "type", "payload", "is_read", "created_at"]
        read_only_fields = fields


class NotificationsPageSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()
    results = NotificationSerializer(many=True)
    next_page = serializers.IntegerField(allow_null=True)


class NotificationsQuerySerializer(serializers.Serializer):
    page = serializers.IntegerField(min_value=1, default=1)


class UnreadSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()


class MarkReadSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, help_text="Empty: all of them."
    )
