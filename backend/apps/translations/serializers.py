from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer
from apps.core import kinds

from .models import DESCRIPTION_MAX, Translation

TRANSLATABLE_KINDS = ["mod", "pack", "server"]


class TranslationSerializer(serializers.ModelSerializer):
    author = UserBriefSerializer(read_only=True)

    class Meta:
        model = Translation
        fields = ["id", "field", "text", "status", "author", "reject_reason", "created_at"]
        read_only_fields = fields


class TranslationsQuerySerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=TRANSLATABLE_KINDS)
    id = serializers.CharField(max_length=96)


class TranslationProposeSerializer(TranslationsQuerySerializer):
    field = serializers.ChoiceField(choices=Translation.Field.choices)
    text = serializers.CharField(max_length=DESCRIPTION_MAX)


class TranslationReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    reason = serializers.CharField(max_length=280, required=False, allow_blank=True)


class QueueItemSerializer(TranslationSerializer):
    kind = serializers.SerializerMethodField()
    target_id = serializers.SerializerMethodField()

    class Meta(TranslationSerializer.Meta):
        fields = [*TranslationSerializer.Meta.fields, "kind", "target_id"]
        read_only_fields = fields

    def get_kind(self, translation: Translation) -> str:
        return kinds.kind_for_model(translation.content_type.model_class()).name

    def get_target_id(self, translation: Translation) -> str:
        kind = kinds.kind_for_model(translation.content_type.model_class())
        target = translation.target
        return kind.identifier(target) if target is not None else ""
