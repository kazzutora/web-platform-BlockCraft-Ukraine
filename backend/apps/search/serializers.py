from rest_framework import serializers

from .services import KIND_ORDER


class SearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField(max_length=100, trim_whitespace=True)
    kind = serializers.ChoiceField(choices=KIND_ORDER, required=False)
    page = serializers.IntegerField(min_value=1, default=1)


class SearchHitSerializer(serializers.Serializer):
    """One found object; the card fields depend on the kind and are null for the others."""

    kind = serializers.CharField()
    id = serializers.CharField()
    title = serializers.CharField()
    summary = serializers.CharField(allow_blank=True)
    image = serializers.CharField(allow_null=True)
    project_type = serializers.CharField(allow_null=True)
    latest_game_version = serializers.CharField(allow_null=True, required=False, default=None)
    loaders = serializers.ListField(child=serializers.CharField())
    author = serializers.CharField(allow_null=True)
    modes = serializers.ListField(child=serializers.CharField())
    color_bucket = serializers.CharField(allow_null=True)
    address = serializers.CharField(allow_null=True, required=False, default=None)
    items_count = serializers.IntegerField(allow_null=True, required=False, default=None)


class SearchGroupSerializer(serializers.Serializer):
    kind = serializers.CharField()
    total = serializers.IntegerField()
    results = SearchHitSerializer(many=True)
    next_page = serializers.IntegerField(allow_null=True)


class SearchResponseSerializer(serializers.Serializer):
    q = serializers.CharField()
    groups = SearchGroupSerializer(many=True)
