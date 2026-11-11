from django.urls import path

from . import views

urlpatterns = [
    path("translations", views.TranslationsView.as_view(), name="translations"),
    path("translations/queue", views.TranslationQueueView.as_view(), name="translations-queue"),
    path(
        "translations/<int:pk>/review",
        views.TranslationReviewView.as_view(),
        name="translations-review",
    ),
]
