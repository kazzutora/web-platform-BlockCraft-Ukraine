from django.contrib import admin

from .models import Review, ReviewVote


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


admin.site.register(ReviewVote)
