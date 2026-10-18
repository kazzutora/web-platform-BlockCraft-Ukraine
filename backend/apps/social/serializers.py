from datetime import timedelta

from rest_framework import serializers

from apps.accounts.serializers import UserBriefSerializer
from apps.core import kinds

from .models import Comment, Review

EDIT_GRACE = timedelta(minutes=1)


class TargetQuerySerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=kinds.names())
    id = serializers.CharField(max_length=96)


class LikeStateSerializer(serializers.Serializer):
    kind = serializers.CharField()
    id = serializers.CharField()
    liked = serializers.BooleanField()
    likes_count = serializers.IntegerField()


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


# Comments


class CommentReplySerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)
    body = serializers.SerializerMethodField()
    is_edited = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "user",
            "body",
            "is_deleted",
            "is_pinned",
            "is_edited",
            "created_at",
            "can_edit",
            "can_delete",
        ]
        read_only_fields = fields

    def _viewer(self):
        request = self.context.get("request")
        return request.user if request else None

    def get_body(self, comment: Comment) -> str:
        return "" if comment.is_deleted else comment.body

    def get_is_edited(self, comment: Comment) -> bool:
        return comment.updated_at - comment.created_at > EDIT_GRACE and not comment.is_deleted

    def get_can_edit(self, comment: Comment) -> bool:
        viewer = self._viewer()
        return bool(viewer and viewer.is_authenticated and viewer.pk == comment.user_id) and not (
            comment.is_deleted
        )

    def get_can_delete(self, comment: Comment) -> bool:
        viewer = self._viewer()
        if not viewer or not viewer.is_authenticated or comment.is_deleted:
            return False
        return (
            viewer.pk == comment.user_id
            or viewer.is_moderator
            or viewer.pk == self.context.get("owner_id")
        )


class CommentSerializer(CommentReplySerializer):
    replies = CommentReplySerializer(many=True, read_only=True)

    class Meta(CommentReplySerializer.Meta):
        fields = [*CommentReplySerializer.Meta.fields, "replies"]
        read_only_fields = fields


class CommentsQuerySerializer(TargetQuerySerializer):
    cursor = serializers.CharField(required=False, allow_blank=True)


class CommentsPageSerializer(serializers.Serializer):
    can_comment = serializers.BooleanField()
    can_pin = serializers.BooleanField()
    comments_count = serializers.IntegerField()
    pinned = CommentSerializer(many=True)
    results = CommentSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class CommentCreateSerializer(TargetQuerySerializer):
    body = serializers.CharField(max_length=1000, trim_whitespace=True)
    parent = serializers.IntegerField(required=False, allow_null=True)


class CommentUpdateSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=1000, trim_whitespace=True)
