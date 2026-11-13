from __future__ import annotations

from django.db.models import Prefetch, ProtectedError, QuerySet
from rest_framework import generics

from core.exceptions import BusinessError
from core.permissions import IsTenantMember

from .models import ServiceCategory, ServiceItem
from .permissions import CatalogPermission
from .serializers import ServiceCategorySerializer, ServiceItemSerializer

PERMISSIONS = [IsTenantMember, CatalogPermission]


class CategoryListView(generics.ListCreateAPIView[ServiceCategory]):
    """Categories with their items: the catalog screen and the quote editor load it in one call."""

    serializer_class = ServiceCategorySerializer
    permission_classes = PERMISSIONS
    pagination_class = None

    def get_queryset(self) -> QuerySet[ServiceCategory]:
        if getattr(self, "swagger_fake_view", False):
            return ServiceCategory.all_tenants.none()
        return ServiceCategory.objects.prefetch_related(
            Prefetch("items", queryset=ServiceItem.objects.order_by("name"))
        )


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView[ServiceCategory]):
    serializer_class = ServiceCategorySerializer
    permission_classes = PERMISSIONS
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self) -> QuerySet[ServiceCategory]:
        if getattr(self, "swagger_fake_view", False):
            return ServiceCategory.all_tenants.none()
        return ServiceCategory.objects.all()

    def perform_destroy(self, instance: ServiceCategory) -> None:
        try:
            instance.delete()
        except ProtectedError as exc:
            raise BusinessError(
                "category_not_empty",
                "Cette catégorie contient des prestations : déplacez-les ou supprimez-les d’abord.",
            ) from exc


class ItemListView(generics.ListCreateAPIView[ServiceItem]):
    serializer_class = ServiceItemSerializer
    permission_classes = PERMISSIONS
    pagination_class = None

    def get_queryset(self) -> QuerySet[ServiceItem]:
        if getattr(self, "swagger_fake_view", False):
            return ServiceItem.all_tenants.none()
        return ServiceItem.objects.select_related("category")


class ItemDetailView(generics.RetrieveUpdateDestroyAPIView[ServiceItem]):
    """Deleting keeps past quotes intact: lines copy label and price when they are added."""

    serializer_class = ServiceItemSerializer
    permission_classes = PERMISSIONS
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self) -> QuerySet[ServiceItem]:
        if getattr(self, "swagger_fake_view", False):
            return ServiceItem.all_tenants.none()
        return ServiceItem.objects.all()
