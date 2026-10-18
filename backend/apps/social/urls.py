from django.urls import path

from . import views

urlpatterns = [
    path("likes", views.LikeView.as_view(), name="likes"),
    path("reviews", views.ReviewsView.as_view(), name="reviews"),
    path("reviews/<int:pk>", views.ReviewDetailView.as_view(), name="review"),
    path("reviews/<int:pk>/vote", views.ReviewVoteView.as_view(), name="review-vote"),
    path("comments", views.CommentsView.as_view(), name="comments"),
    path("comments/<int:pk>", views.CommentDetailView.as_view(), name="comment"),
    path("comments/<int:pk>/pin", views.CommentPinView.as_view(), name="comment-pin"),
]
