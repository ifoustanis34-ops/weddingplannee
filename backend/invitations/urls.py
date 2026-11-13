from django.urls import path

from . import views

urlpatterns = [
    path(
        "weddings/<uuid:pk>/ticket-design", views.TicketDesignView.as_view(), name="ticket-design"
    ),
    path("weddings/<uuid:pk>/guests", views.GuestListView.as_view(), name="wedding-guests"),
    path("weddings/<uuid:pk>/guests/import", views.GuestImportView.as_view(), name="guest-import"),
    path(
        "weddings/<uuid:pk>/tickets/generate",
        views.GenerateTicketsView.as_view(),
        name="tickets-generate",
    ),
    path(
        "weddings/<uuid:pk>/tickets/export",
        views.ExportTicketsView.as_view(),
        name="tickets-export",
    ),
    path("guests/<uuid:pk>", views.GuestDetailView.as_view(), name="guest-detail"),
    path("ticket-batches/<str:batch>", views.TicketBatchView.as_view(), name="ticket-batch"),
    path("tickets/preview", views.TicketPreviewView.as_view(), name="ticket-preview"),
    path("tickets/<uuid:pk>/pdf", views.TicketPdfView.as_view(), name="ticket-pdf"),
    path("tickets/<uuid:pk>/cancel", views.CancelTicketView.as_view(), name="ticket-cancel"),
    path("tickets/<uuid:pk>/reissue", views.ReissueTicketView.as_view(), name="ticket-reissue"),
    path("public/tickets/<str:token>", views.PublicTicketView.as_view(), name="public-ticket"),
    path(
        "public/tickets/<str:token>/image",
        views.PublicTicketImageView.as_view(),
        name="public-ticket-image",
    ),
    path(
        "public/tickets/<str:token>/pdf",
        views.PublicTicketPdfView.as_view(),
        name="public-ticket-pdf",
    ),
    path(
        "public/tickets/<str:token>/ics",
        views.PublicTicketIcsView.as_view(),
        name="public-ticket-ics",
    ),
    path(
        "public/tickets/<str:token>/rsvp",
        views.PublicRsvpView.as_view(),
        name="public-ticket-rsvp",
    ),
]
