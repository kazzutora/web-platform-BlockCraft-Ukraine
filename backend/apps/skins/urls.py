from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter(trailing_slash=False)
router.register("skins", views.SkinViewSet, basename="skins")

urlpatterns = [
    path("me/skins", views.MySkinsView.as_view(), name="me-skins"),
    path("me/skin", views.CurrentSkinView.as_view(), name="me-skin"),
    *router.urls,
]
