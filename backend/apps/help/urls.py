from django.urls import path

from . import views

urlpatterns = [
    path("help/crash", views.CrashView.as_view(), name="help-crash"),
    path("help/goals/preview", views.GoalsPreviewView.as_view(), name="help-goals-preview"),
    path("help/goals/pack", views.GoalsPackView.as_view(), name="help-goals-pack"),
]
