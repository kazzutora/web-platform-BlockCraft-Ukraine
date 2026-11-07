from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter(trailing_slash=False)
router.register("packs", views.PackViewSet, basename="packs")

urlpatterns = [
    path("me/packs", views.MyPacksView.as_view(), name="me-packs"),
    *router.urls,
]
