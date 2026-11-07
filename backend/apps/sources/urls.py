from django.urls import path

from . import views

urlpatterns = [
    path("meta", views.MetaView.as_view(), name="meta"),
]
