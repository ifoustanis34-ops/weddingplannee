from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.filters import OrderingFilter
from rest_framework.request import Request
from rest_framework.response import Response

from core.pagination import DefaultCursorPagination
from core.permissions import IsTenantMember
from finance.visibility import can_see_balances

from . import selectors, services
from .filters import ClientFilter
from .models import Client
from .permissions import ClientPermission
from .serializers import ClientHistorySerializer, ClientSerializer

PERMISSIONS = [IsTenantMember, ClientPermission]


def _role(request: Request) -> str | None:
    membership = getattr(request, "membership", None)
    return membership.role if membership is not None else None


MONEY_ORDERING = frozenset({"revenue", "balance_due"})


class ClientOrdering(OrderingFilter):
    """Never sort by amounts the role cannot see: the order itself would leak them.

    The cursor pagination asks this filter for the ordering too, so the rule holds for both.
    """

    def get_ordering(self, request: Request, queryset: QuerySet[Client], view: Any) -> Any:
        ordering = super().get_ordering(request, queryset, view)
        if can_see_balances(_role(request)):
            return ordering
        kept = [field for field in ordering or [] if field.lstrip("-") not in MONEY_ORDERING]
        return kept or ["name"]


class ClientPagination(DefaultCursorPagination):
    ordering = "name"
    max_page_size = 300


class ClientListView(generics.ListCreateAPIView[Client]):
    """`?archived=false` by default. Sort by `revenue` or `balance_due` (money roles only)."""

    serializer_class = ClientSerializer
    permission_classes = PERMISSIONS
    pagination_class = ClientPagination
    filter_backends = [DjangoFilterBackend, ClientOrdering]
    filterset_class = ClientFilter
    ordering_fields = ["name", "created_at", "revenue", "balance_due", "last_order_at"]

    def get_queryset(self) -> QuerySet[Client]:
        if getattr(self, "swagger_fake_view", False):  # OpenAPI generation has no tenant
            return Client.all_tenants.none()
        queryset = selectors.with_metrics(selectors.active_clients())
        if "archived" not in self.request.query_params:
            queryset = queryset.filter(is_archived=False)
        return queryset

    def perform_create(self, serializer: ClientSerializer) -> None:  # type: ignore[override]
        client = services.create_client(
            dict(serializer.validated_data), user=self.request.user  # type: ignore[arg-type]
        )
        serializer.instance = selectors.with_metrics(Client.objects.filter(pk=client.pk)).get()


class ClientDetailView(generics.RetrieveUpdateDestroyAPIView[Client]):
    serializer_class = ClientSerializer
    permission_classes = PERMISSIONS
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self) -> QuerySet[Client]:
        if getattr(self, "swagger_fake_view", False):  # OpenAPI generation has no tenant
            return Client.all_tenants.none()
        return selectors.with_metrics(selectors.active_clients())

    def perform_update(self, serializer: ClientSerializer) -> None:  # type: ignore[override]
        assert serializer.instance is not None
        services.update_client(serializer.instance, dict(serializer.validated_data))
        serializer.instance = self.get_queryset().get(pk=serializer.instance.pk)

    def perform_destroy(self, instance: Client) -> None:
        services.delete_client(instance, request=self.request)


class ClientHistoryView(generics.GenericAPIView[Client]):
    """Quotes, contracts and payments of a client (amounts hidden from the assistant)."""

    permission_classes = PERMISSIONS
    serializer_class = ClientHistorySerializer

    def get_queryset(self) -> QuerySet[Client]:
        if getattr(self, "swagger_fake_view", False):  # OpenAPI generation has no tenant
            return Client.all_tenants.none()
        return selectors.active_clients()

    @extend_schema(responses=ClientHistorySerializer)
    def get(self, request: Request, pk: str) -> Response:
        client = self.get_object()
        data = dict(ClientHistorySerializer(selectors.history(client)).data)
        if not can_see_balances(_role(request)):
            for key in ("quotes", "contracts"):
                data[key] = [{**row, "total": None} for row in data[key]]
            data["reservations"] = [
                {**row, "total": None, "balance": None} for row in data["reservations"]
            ]
            data["payments"] = []
        return Response(data)
