from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("api/v1/", include("core.urls")),
    path("api/schema", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

# Django admin (« Super-admin », CLAUDE.md): always in development; in production only when
# DJANGO_ADMIN_URL is set, at that address (pick one that is not guessable).
if settings.DJANGO_ADMIN_URL:
    urlpatterns.append(path(settings.DJANGO_ADMIN_URL, admin.site.urls))

admin.site.site_header = "Wedivo — administration"
admin.site.site_title = "Wedivo"
admin.site.index_title = "Plateforme"
