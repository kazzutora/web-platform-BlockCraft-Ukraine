from rest_framework import serializers

CHECK_STATUS_CHOICES = ["ok", "error"]


class HealthChecksSerializer(serializers.Serializer):
    database = serializers.ChoiceField(choices=CHECK_STATUS_CHOICES)
    redis = serializers.ChoiceField(choices=CHECK_STATUS_CHOICES)


class HealthSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=CHECK_STATUS_CHOICES)
    checks = HealthChecksSerializer()


class JobSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.CharField(help_text="What runs, e.g. mods.import.")
    status = serializers.ChoiceField(choices=["queued", "running", "done", "failed"])
    result = serializers.DictField(
        allow_null=True, help_text="What the job produced, e.g. {slug, project_type}."
    )
    error = serializers.CharField(
        allow_blank=True, help_text="Error code when failed: not_found, unsupported_type, …"
    )
