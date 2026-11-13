from django.urls import path

from . import views

urlpatterns = [
    path("reservations", views.ReservationListView.as_view(), name="reservation-list"),
    path("reservations/stats", views.StatsView.as_view(), name="reservation-stats"),
    path("reservations/export", views.ExportView.as_view(), name="reservation-export"),
    path(
        "reservations/<uuid:pk>", views.ReservationDetailView.as_view(), name="reservation-detail"
    ),
    path("reservations/<uuid:pk>/confirm", views.ConfirmView.as_view(), name="reservation-confirm"),
    path("reservations/<uuid:pk>/move", views.MoveView.as_view(), name="reservation-move"),
    path("reservations/<uuid:pk>/status", views.StatusView.as_view(), name="reservation-status"),
    path(
        "reservations/<uuid:pk>/checkout", views.CheckoutView.as_view(), name="reservation-checkout"
    ),
    path("reservations/<uuid:pk>/return", views.ReturnView.as_view(), name="reservation-return"),
    path("reservations/<uuid:pk>/cancel", views.CancelView.as_view(), name="reservation-cancel"),
    path(
        "reservations/<uuid:pk>/payments", views.PaymentView.as_view(), name="reservation-payments"
    ),
    path(
        "reservations/<uuid:pk>/security", views.SecurityView.as_view(), name="reservation-security"
    ),
    path(
        "reservations/<uuid:pk>/shortages",
        views.ShortageView.as_view(),
        name="reservation-shortages",
    ),
    path(
        "reservations/<uuid:pk>/document", views.DocumentView.as_view(), name="reservation-document"
    ),
    path(
        "reservation-payments/<uuid:pk>/cancel",
        views.PaymentCancelView.as_view(),
        name="reservation-payment-cancel",
    ),
]
