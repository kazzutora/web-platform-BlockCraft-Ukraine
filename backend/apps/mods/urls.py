from rest_framework.routers import SimpleRouter

from .views import CategoryViewSet, ModViewSet

router = SimpleRouter(trailing_slash=False)
router.register("mods", ModViewSet, basename="mods")
router.register("categories", CategoryViewSet, basename="categories")

urlpatterns = router.urls
