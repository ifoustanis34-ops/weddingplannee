from django.urls import path

from . import views

urlpatterns = [
    path("clients", views.ClientListView.as_view(), name="client-list"),
    path("clients/<uuid:pk>", views.ClientDetailView.as_view(), name="client-detail"),
    path("clients/<uuid:pk>/history", views.ClientHistoryView.as_view(), name="client-history"),
]
