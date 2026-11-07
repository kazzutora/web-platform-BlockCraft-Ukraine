from django.urls import path

from . import views

urlpatterns = [
    path("meta", views.MetaView.as_view(), name="meta"),
    path("sources", views.SourcesView.as_view(), name="sources"),
]
