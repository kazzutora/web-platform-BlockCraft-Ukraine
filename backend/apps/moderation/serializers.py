from rest_framework import serializers

from apps.core import kinds

from .models import Report


class ReportCreateSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=[*kinds.names(), "comment"])
    id = serializers.CharField(max_length=96)
    reason = serializers.ChoiceField(choices=Report.Reason.choices)
    comment = serializers.CharField(max_length=500, required=False, allow_blank=True)


class ReportCreatedSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.CharField()
