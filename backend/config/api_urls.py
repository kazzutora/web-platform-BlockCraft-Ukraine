from django.urls import include, path

urlpatterns = [
    path("", include("apps.core.urls")),
    path("", include("apps.accounts.urls")),
    path("", include("apps.mods.urls")),
    path("", include("apps.skins.urls")),
    path("", include("apps.servers.urls")),
    path("", include("apps.library.urls")),
    path("", include("apps.social.urls")),
]
