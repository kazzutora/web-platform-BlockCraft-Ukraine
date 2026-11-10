from django.urls import path

from .views import IdentifyView, ResolveView, UpdatesView

urlpatterns = [
    path("compat/resolve", ResolveView.as_view(), name="compat-resolve"),
    path("compat/identify", IdentifyView.as_view(), name="compat-identify"),
    path("compat/updates", UpdatesView.as_view(), name="compat-updates"),
]
