from django.urls import include, path

from .signed_files import serve as serve_signed_file
from .views import ExportView, HealthView, SearchView

urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
    path("search", SearchView.as_view(), name="search"),
    path("exports/<slug:kind>", ExportView.as_view(), name="export"),
    path("files/<str:token>", serve_signed_file, name="signed-file"),
    path("", include("accounts.urls")),
    path("", include("organizations.urls")),
    path("", include("crm.urls")),
    path("", include("catalog.urls")),
    path("", include("quotes.urls")),
    path("", include("contracts.urls")),
    path("", include("finance.urls")),
    path("", include("alerts.urls")),
    path("", include("notifications.urls")),
    path("", include("stock.urls")),
    path("", include("reservations.urls")),
    path("", include("staff.urls")),
    path("", include("events.urls")),
    path("", include("vendors.urls")),
    path("", include("invitations.urls")),
    path("", include("documents.urls")),
    path("", include("floorplans.urls")),
    path("", include("platform_admin.urls")),
]
