from django.urls import path

from . import views

urlpatterns = [
    path("contracts", views.ContractListView.as_view(), name="contract-list"),
    path("contracts/<uuid:pk>", views.ContractDetailView.as_view(), name="contract-detail"),
    path(
        "contracts/<uuid:pk>/payments", views.RecordPaymentView.as_view(), name="contract-payments"
    ),
    path("contracts/<uuid:pk>/schedule", views.ScheduleView.as_view(), name="contract-schedule"),
    path("payments/<uuid:pk>/cancel", views.CancelPaymentView.as_view(), name="payment-cancel"),
    path("payments/<uuid:pk>/receipt", views.ReceiptView.as_view(), name="payment-receipt"),
    path("payments/<uuid:pk>/proof", views.ProofView.as_view(), name="payment-proof"),
]
