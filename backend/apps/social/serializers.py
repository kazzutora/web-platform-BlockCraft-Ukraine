from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer
from apps.core import kinds

from .models import Review


class TargetQuerySerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=kinds.names())
    id = serializers.CharField(max_length=96)


# Reviews


class ReviewSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)
    is_mine = serializers.SerializerMethodField()
    my_vote = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "user",
            "stars",
            "text",
            "helpful_count",
            "created_at",
            "updated_at",
            "is_mine",
            "my_vote",
        ]
        read_only_fields = fields

    def get_is_mine(self, review: Review) -> bool:
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and review.user_id == request.user.pk)

    def get_my_vote(self, review: Review) -> bool | None:
        """True: «корисно», False: «не корисно», null: no vote (annotated by the view)."""
        return getattr(review, "my_vote", None)


class ReviewsQuerySerializer(TargetQuerySerializer):
    sort = serializers.ChoiceField(choices=["helpful", "new"], default="helpful")
    page = serializers.IntegerField(min_value=1, default=1)


class ReviewSummarySerializer(serializers.Serializer):
    rating_avg = serializers.FloatField()
    rating_count = serializers.IntegerField()
    distribution = serializers.DictField(child=serializers.IntegerField())
    my_review = ReviewSerializer(allow_null=True)


class ReviewsPageSerializer(serializers.Serializer):
    summary = ReviewSummarySerializer()
    count = serializers.IntegerField()
    next_page = serializers.IntegerField(allow_null=True)
    results = ReviewSerializer(many=True)


class ReviewUpsertSerializer(TargetQuerySerializer):
    stars = serializers.IntegerField(min_value=1, max_value=5)
    text = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class ReviewVoteSerializer(serializers.Serializer):
    is_helpful = serializers.BooleanField()
