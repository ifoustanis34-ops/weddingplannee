from django.urls import path

from . import views

urlpatterns = [
    path("vendors", views.VendorListView.as_view(), name="vendor-list"),
    path("vendors/<uuid:pk>", views.VendorDetailView.as_view(), name="vendor-detail"),
    path("weddings/<uuid:pk>/vendors", views.WeddingVendorsView.as_view(), name="wedding-vendors"),
    path(
        "vendor-assignments/<uuid:pk>",
        views.AssignmentDetailView.as_view(),
        name="vendor-assignment-detail",
    ),
]
