from rest_framework import serializers

CHECK_STATUS_CHOICES = ["ok", "error"]


class HealthChecksSerializer(serializers.Serializer):
    database = serializers.ChoiceField(choices=CHECK_STATUS_CHOICES)
    redis = serializers.ChoiceField(choices=CHECK_STATUS_CHOICES)


class HealthSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=CHECK_STATUS_CHOICES)
    checks = HealthChecksSerializer()
