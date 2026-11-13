from __future__ import annotations

from typing import Any

from django.db import transaction
from django.db.models import ProtectedError, QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.request import Request
from rest_framework.response import Response

from core.exceptions import BusinessError
from events.models import Wedding
from events.permissions import PERMISSIONS, WEDDING_PERMISSIONS
from finance.permissions import role_of
from finance.visibility import can_see_balances

from . import selectors
from .models import Vendor, VendorAssignment
from .serializers import MONEY_FIELDS, AssignmentSerializer, VendorSerializer, strip_money


class MoneyAware:
    """Amounts are hidden from, and not accepted from, roles without access to money (§11)."""

    def _request(self) -> Request:
        request: Request = self.request  # type: ignore[attr-defined]
        return request

    def sees_money(self) -> bool:
        return can_see_balances(role_of(self._request()))

    def shape(self, data: Any) -> Any:
        if self.sees_money():
            return data
        if isinstance(data, list):
            return [strip_money(item) for item in data]
        return strip_money(data)

    def clean_input(self) -> dict[str, Any]:
        data = dict(self._request().data.items())
        if not self.sees_money():
            for key in MONEY_FIELDS:
                data.pop(key, None)
        return data


class VendorListView(MoneyAware, generics.ListCreateAPIView[Vendor]):
    """Directory of suppliers and partners (complement §13). `?category=`, `?kind=` filter."""

    serializer_class = VendorSerializer
    permission_classes = PERMISSIONS
    pagination_class = None

    def get_queryset(self) -> QuerySet[Vendor]:
        if getattr(self, "swagger_fake_view", False):
            return Vendor.all_tenants.none()
        vendors = selectors.vendors_with_stats()
        params = self.request.query_params
        if params.get("category"):
            vendors = vendors.filter(category=params["category"])
        if params.get("kind") in Vendor.Kind.values:
            vendors = vendors.filter(kind=params["kind"])
        return vendors

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return Response(self.shape(super().list(request, *args, **kwargs).data))

    def perform_create(self, serializer: VendorSerializer) -> None:  # type: ignore[override]
        serializer.save(created_by=self.request.user)


class VendorDetailView(MoneyAware, generics.RetrieveUpdateDestroyAPIView[Vendor]):
    serializer_class = VendorSerializer
    permission_classes = PERMISSIONS
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self) -> QuerySet[Vendor]:
        if getattr(self, "swagger_fake_view", False):
            return Vendor.all_tenants.none()
        return selectors.vendors_with_stats()

    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return Response(self.shape(super().retrieve(request, *args, **kwargs).data))

    def perform_destroy(self, instance: Vendor) -> None:
        """Feedback 13/11/2026: owner and planner delete; a contact that worked on weddings
        leaves the address book but stays on those weddings (amounts still owed included)."""
        from accounts.models import Membership
        from core import audit

        membership = getattr(self.request, "membership", None)
        if membership is None or membership.role not in (
            Membership.Role.OWNER,
            Membership.Role.PLANNER,
        ):
            raise BusinessError(
                "forbidden",
                "Seuls le propriétaire et le planner suppriment un contact.",
                status_code=403,
            )
        audit.record(
            "vendor.deleted", instance, request=self.request, changes={"name": instance.name}
        )
        try:
            with transaction.atomic():
                instance.delete()
        except ProtectedError:
            instance.is_deleted = True
            instance.save(update_fields=["is_deleted", "updated_at"])


class WeddingVendorsView(MoneyAware, generics.ListCreateAPIView[VendorAssignment]):
    """Vendors booked for a wedding, with the service, the cost and what was paid."""

    serializer_class = AssignmentSerializer
    permission_classes = WEDDING_PERMISSIONS
    pagination_class = None

    def wedding(self) -> Wedding:
        wedding: Wedding = get_object_or_404(Wedding.objects.all(), pk=self.kwargs["pk"])
        return wedding

    def get_queryset(self) -> QuerySet[VendorAssignment]:
        if getattr(self, "swagger_fake_view", False):
            return VendorAssignment.all_tenants.none()
        return VendorAssignment.objects.filter(wedding=self.wedding()).select_related(
            "vendor", "wedding"
        )

    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return Response(self.shape(super().list(request, *args, **kwargs).data))

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = AssignmentSerializer(data=self.clean_input())
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save(wedding=self.wedding(), created_by=request.user)
        return Response(self.shape(AssignmentSerializer(assignment).data), status=201)


class AssignmentDetailView(MoneyAware, generics.RetrieveUpdateDestroyAPIView[VendorAssignment]):
    serializer_class = AssignmentSerializer
    permission_classes = WEDDING_PERMISSIONS
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self) -> QuerySet[VendorAssignment]:
        if getattr(self, "swagger_fake_view", False):
            return VendorAssignment.all_tenants.none()
        return VendorAssignment.objects.select_related("vendor", "wedding")

    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return Response(self.shape(super().retrieve(request, *args, **kwargs).data))

    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        assignment = self.get_object()
        serializer = AssignmentSerializer(assignment, data=self.clean_input(), partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self.shape(AssignmentSerializer(assignment).data))
