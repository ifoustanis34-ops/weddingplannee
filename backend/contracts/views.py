from __future__ import annotations

from typing import Any

from django.db.models import Q, QuerySet
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.models import User
from core.permissions import IsTenantMember
from finance.permissions import FinancePermission, role_of
from finance.selectors import contracts_with_metrics

from . import pdf, services
from .models import Contract, Payment
from .serializers import (
    CancelPaymentSerializer,
    ContractDetailSerializer,
    ContractListSerializer,
    PaymentInputSerializer,
    PaymentSerializer,
    ScheduleInputSerializer,
)

PERMISSIONS = [IsTenantMember, FinancePermission]


class ContractQuerysetMixin:
    def get_queryset(self) -> QuerySet[Contract]:
        if getattr(self, "swagger_fake_view", False):
            return Contract.all_tenants.none()
        return (
            contracts_with_metrics()
            .select_related("quote")
            .prefetch_related("payments__recorded_by", "schedule", "wedding__expenses")
        )

    def get_serializer_context(self) -> dict[str, Any]:
        context: dict[str, Any] = super().get_serializer_context()  # type: ignore[misc]
        context["role"] = role_of(self.request)  # type: ignore[attr-defined]
        return context


class ContractListView(ContractQuerysetMixin, generics.ListAPIView[Contract]):
    serializer_class = ContractListSerializer
    permission_classes = PERMISSIONS
    pagination_class = None

    def get_queryset(self) -> QuerySet[Contract]:
        queryset = super().get_queryset().order_by("wedding_date", "number")
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        term = self.request.query_params.get("search", "").strip()
        if term:
            queryset = queryset.filter(Q(number__icontains=term) | Q(client__name__icontains=term))
        return queryset


class ContractDetailView(ContractQuerysetMixin, generics.RetrieveAPIView[Contract]):
    serializer_class = ContractDetailSerializer
    permission_classes = PERMISSIONS


class ContractActionView(ContractQuerysetMixin, generics.GenericAPIView[Contract]):
    permission_classes = PERMISSIONS

    def detail(self, contract: Contract, code: int = status.HTTP_200_OK) -> Response:
        fresh = self.get_queryset().get(pk=contract.pk)
        return Response(
            ContractDetailSerializer(fresh, context=self.get_serializer_context()).data, status=code
        )

    @property
    def user(self) -> User:
        return self.request.user  # type: ignore[return-value]


class RecordPaymentView(ContractActionView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(request=PaymentInputSerializer, responses={201: ContractDetailSerializer})
    def post(self, request: Request, pk: str) -> Response:
        contract = self.get_object()
        serializer = PaymentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.record_payment(
            contract, user=self.user, request=request, **serializer.validated_data
        )
        return self.detail(contract, status.HTTP_201_CREATED)


class ScheduleView(ContractActionView):
    @extend_schema(request=ScheduleInputSerializer, responses=ContractDetailSerializer)
    def put(self, request: Request, pk: str) -> Response:
        contract = self.get_object()
        serializer = ScheduleInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lines = [
            services.ScheduleLine(**line) for line in serializer.validated_data["installments"]
        ]
        services.replace_schedule(contract, lines, user=self.user, request=request)
        return self.detail(contract)


class PaymentQuerysetMixin:
    def get_queryset(self) -> QuerySet[Payment]:
        if getattr(self, "swagger_fake_view", False):
            return Payment.all_tenants.none()
        return Payment.objects.select_related(
            "contract__client", "contract__organization", "recorded_by"
        )


class CancelPaymentView(PaymentQuerysetMixin, generics.GenericAPIView[Payment]):
    permission_classes = PERMISSIONS

    @extend_schema(request=CancelPaymentSerializer, responses=PaymentSerializer)
    def post(self, request: Request, pk: str) -> Response:
        payment = self.get_object()
        serializer = CancelPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.cancel_payment(
            payment,
            reason=serializer.validated_data["reason"],
            user=request.user,  # type: ignore[arg-type]
            request=request,
        )
        return Response(PaymentSerializer(payment).data)


class ReceiptView(PaymentQuerysetMixin, generics.GenericAPIView[Payment]):
    permission_classes = PERMISSIONS

    @extend_schema(responses={(200, "application/pdf"): bytes})
    def get(self, request: Request, pk: str) -> HttpResponse:
        payment = self.get_object()
        content = payment.receipt_file.read() if payment.receipt_file else pdf.render_pdf(payment)
        response = HttpResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{pdf.filename(payment)}"'
        return response


class ProofView(PaymentQuerysetMixin, generics.GenericAPIView[Payment]):
    permission_classes = PERMISSIONS

    @extend_schema(responses={(200, "application/octet-stream"): bytes})
    def get(self, request: Request, pk: str) -> HttpResponse:
        payment = self.get_object()
        if not payment.proof:
            from django.http import Http404

            raise Http404
        response = HttpResponse(payment.proof.read(), content_type="application/octet-stream")
        response["Content-Disposition"] = (
            f'attachment; filename="{payment.proof.name.rsplit("/", 1)[-1]}"'
        )
        return response
