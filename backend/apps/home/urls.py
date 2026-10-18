from django.urls import path

from . import views

urlpatterns = [
    path("home", views.HomeView.as_view(), name="home"),
    path("top", views.TopView.as_view(), name="top"),
]
