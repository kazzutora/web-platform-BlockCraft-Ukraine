from django.urls import path

from .views import ResolveView

urlpatterns = [
    path("compat/resolve", ResolveView.as_view(), name="compat-resolve"),
]
