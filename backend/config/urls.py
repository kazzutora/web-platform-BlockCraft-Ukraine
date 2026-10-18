from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("config.api_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    # allauth headless API for the SPA; with HEADLESS_ONLY `accounts/` serves only
    # the OAuth provider callbacks
    path("_allauth/", include("allauth.headless.urls")),
    path("accounts/", include("allauth.urls")),
]
