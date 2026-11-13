from __future__ import annotations

from datetime import date
from typing import Any

from django.db.models import QuerySet
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core import audit
from core.exceptions import BusinessError
from core.permissions import IsTenantMember
from core.tenant import require_current_organization

from . import dashboard, exports, selectors
from .models import Expense, ExpenseCategory
from .periods import PERIODS
from .permissions import FinancePermission, role_of
from .serializers import ExpenseCategorySerializer, ExpenseSerializer
from .visibility import strip_for_role

PERMISSIONS = [IsTenantMember, FinancePermission]


class ExpenseListView(generics.ListCreateAPIView[Expense]):
    """Expenses feed the margin: owner and accountant only (CLAUDE.md §11)."""

    serializer_class = ExpenseSerializer
    permission_classes = PERMISSIONS
    pagination_class = None
    margins_only = True

    def get_queryset(self) -> QuerySet[Expense]:
        if getattr(self, "swagger_fake_view", False):
            return Expense.all_tenants.none()
        queryset = Expense.objects.select_related("wedding", "category")
        wedding = self.request.query_params.get("wedding")
        contract = self.request.query_params.get("contract")
        if wedding:
            queryset = queryset.filter(wedding_id=wedding)
        if contract:
            queryset = queryset.filter(wedding__contract_id=contract)
        return queryset

    def perform_create(self, serializer: ExpenseSerializer) -> None:  # type: ignore[override]
        # « Enregistrer une dépense » from the dashboard: dated today unless told otherwise.
        date = serializer.validated_data.get("date") or timezone.localdate()
        serializer.save(created_by=self.request.user, date=date)


class ExpenseCategoryListView(generics.ListCreateAPIView[ExpenseCategory]):
    """Editable categories (reservations-stock.md §6.2): owner and accountant."""

    serializer_class = ExpenseCategorySerializer
    permission_classes = PERMISSIONS
    pagination_class = None
    margins_only = True

    def get_queryset(self) -> QuerySet[ExpenseCategory]:
        if getattr(self, "swagger_fake_view", False):
            return ExpenseCategory.all_tenants.none()
        return ExpenseCategory.objects.all()

    def perform_create(self, serializer: ExpenseCategorySerializer) -> None:  # type: ignore[override]
        last = ExpenseCategory.objects.order_by("-position").first()
        serializer.save(created_by=self.request.user, position=(last.position + 1) if last else 0)


class ExpenseCategoryDetailView(generics.RetrieveUpdateAPIView[ExpenseCategory]):
    """Rename or deactivate; never deleted (its expenses keep it)."""

    serializer_class = ExpenseCategorySerializer
    permission_classes = PERMISSIONS
    http_method_names = ["get", "patch"]
    margins_only = True

    def get_queryset(self) -> QuerySet[ExpenseCategory]:
        if getattr(self, "swagger_fake_view", False):
            return ExpenseCategory.all_tenants.none()
        return ExpenseCategory.objects.all()


class ExpenseDetailView(generics.RetrieveUpdateDestroyAPIView[Expense]):
    serializer_class = ExpenseSerializer
    permission_classes = PERMISSIONS
    http_method_names = ["get", "patch", "delete"]
    margins_only = True

    def get_queryset(self) -> QuerySet[Expense]:
        if getattr(self, "swagger_fake_view", False):
            return Expense.all_tenants.none()
        return Expense.objects.all()

    def perform_destroy(self, instance: Expense) -> None:
        audit.record(
            "expense.deleted",
            instance,
            request=self.request,
            changes={"label": instance.label, "amount": instance.amount},
        )
        instance.delete()


class FinanceSummaryView(APIView):
    permission_classes = PERMISSIONS

    @extend_schema(responses={200: OpenApiResponse(description="Totaux financiers")})
    def get(self, request: Request) -> Response:
        return Response(strip_for_role(selectors.finance_summary(), role_of(request)))


class FinanceExportView(APIView):
    permission_classes = PERMISSIONS
    margins_only = True

    @extend_schema(
        # Not `format`: DRF reserves that query parameter for content negotiation.
        parameters=[OpenApiParameter("type", enum=["csv", "xlsx"])],
        responses={(200, "application/octet-stream"): bytes},
    )
    def get(self, request: Request) -> HttpResponse:
        fmt = request.query_params.get("type", "csv")
        if fmt not in ("csv", "xlsx"):
            raise BusinessError("invalid", "Format inconnu : csv ou xlsx.")
        organization = require_current_organization()
        stamp = timezone.localdate().isoformat()
        if fmt == "csv":
            response = HttpResponse(exports.to_csv(), content_type="text/csv; charset=utf-8")
        else:
            response = HttpResponse(
                exports.to_xlsx(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        response["Content-Disposition"] = (
            f'attachment; filename="contrats-{organization.slug}-{stamp}.{fmt}"'
        )
        audit.record("finance.exported", organization, request=request, changes={"format": fmt})
        return response


class AnyMember(BasePermission):
    """Every member gets a dashboard; money blocks are filtered by role."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return True


class DashboardView(APIView):
    permission_classes = [IsTenantMember, AnyMember]
    open_to_field_roles = True  # filtered by role: no amount for them

    @extend_schema(
        parameters=[
            OpenApiParameter("period", enum=list(PERIODS), default="month"),
            OpenApiParameter("from", OpenApiTypes.DATE, description="période personnalisée"),
            OpenApiParameter("to", OpenApiTypes.DATE, description="période personnalisée"),
        ],
        responses={200: OpenApiResponse(description="Tableau de bord de la période")},
    )
    def get(self, request: Request) -> Response:
        params = request.query_params
        try:
            start = date.fromisoformat(params["from"]) if params.get("from") else None
            end = date.fromisoformat(params["to"]) if params.get("to") else None
        except ValueError as exc:
            raise BusinessError("invalid", "Date illisible (AAAA-MM-JJ).") from exc
        data: dict[str, Any] = dashboard.summary_for(
            role_of(request), params.get("period", "month"), start, end
        )
        return Response(data)
