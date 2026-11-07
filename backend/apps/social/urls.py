from django.urls import path

from . import views

urlpatterns = [
    path("reviews", views.ReviewsView.as_view(), name="reviews"),
    path("reviews/<int:pk>", views.ReviewDetailView.as_view(), name="review"),
    path("reviews/<int:pk>/vote", views.ReviewVoteView.as_view(), name="review-vote"),
]
