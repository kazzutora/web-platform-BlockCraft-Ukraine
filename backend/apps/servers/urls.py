from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter(trailing_slash=False)
router.register("servers", views.ServerViewSet, basename="servers")

urlpatterns = [
    path("me/servers", views.MyServersView.as_view(), name="me-servers"),
    *router.urls,
]
