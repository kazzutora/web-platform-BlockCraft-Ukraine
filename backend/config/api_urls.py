from django.urls import include, path

urlpatterns = [
    path("", include("apps.core.urls")),
    path("", include("apps.accounts.urls")),
    path("", include("apps.mods.urls")),
    path("", include("apps.skins.urls")),
    path("", include("apps.servers.urls")),
    path("", include("apps.search.urls")),
    path("", include("apps.home.urls")),
    path("", include("apps.notifications.urls")),
    path("", include("apps.moderation.urls")),
    path("", include("apps.library.urls")),
    path("", include("apps.social.urls")),
]
