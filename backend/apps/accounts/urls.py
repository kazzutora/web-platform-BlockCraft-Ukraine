from django.urls import path

from . import views

urlpatterns = [
    path("csrf", views.CsrfView.as_view(), name="csrf"),
    path("me", views.MeView.as_view(), name="me"),
    path("me/export", views.MeExportView.as_view(), name="me-export"),
    path("me/game-profile", views.MeGameProfileView.as_view(), name="me-game-profile"),
    path("me/settings", views.MeSettingsView.as_view(), name="me-settings"),
    path("me/onboarding", views.OnboardingView.as_view(), name="me-onboarding"),
    path("me/avatar", views.MeAvatarView.as_view(), name="me-avatar"),
    path("users/<str:nickname>", views.UserProfileView.as_view(), name="user-profile"),
]
