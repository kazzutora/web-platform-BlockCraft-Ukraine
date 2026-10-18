from django.contrib import admin

from .models import Comment, Like, Review, ReviewVote


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "content_type",
        "object_id",
        "stars",
        "helpful_count",
        "status",
        "created_at",
    ]
    list_filter = ["status", "stars", "content_type"]
    search_fields = ["user__nickname", "text"]
    raw_id_fields = ["user"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "content_type",
        "object_id",
        "short_body",
        "is_pinned",
        "status",
        "created_at",
    ]
    list_filter = ["status", "is_pinned", "is_deleted", "content_type"]
    search_fields = ["user__nickname", "body"]
    raw_id_fields = ["user", "parent"]

    @admin.display(description="текст")
    def short_body(self, comment: Comment) -> str:
        return comment.body[:80]


admin.site.register(Like)
admin.site.register(ReviewVote)
