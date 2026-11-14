from __future__ import annotations

import csv
import io
from typing import Any

from django.db.models import QuerySet
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core import audit
from core.exceptions import BusinessError
from core.permissions import IsTenantMember
from core.tenant import require_current_organization
from finance.visibility import can_see_balances, can_see_margins

from . import documents, partners, selectors, services
from .models import Reservation, ReservationLine, ReservationPayment
from .permissions import EDIT, LOGISTICS, PAYMENTS, ReservationPermission, role_of
from .serializers import (
    CancelSerializer,
    CheckoutSerializer,
    MoveSerializer,
    PartnerAssignSerializer,
    PaymentInputSerializer,
    PaymentSerializer,
    ReservationListSerializer,
    ReservationSerializer,
    ReturnSerializer,
    SecuritySerializer,
    StatusSerializer,
    line_inputs,
)


class ReservationView:
    permission_classes: Any = [IsTenantMember, ReservationPermission]
    open_to_field_roles = True  # the storekeeper loads and receives the equipment


def _detail(request: Request, pk: Any) -> Response:
    reservation = (
        selectors.with_money()
        .prefetch_related(
            "lines__item",
            "lines__partner_supply__vendor",
            "payments__recorded_by",
            "logs__author",
        )
        .get(pk=pk)
    )
    return Response(ReservationSerializer(reservation, context={"request": request}).data)


def _get(pk: Any) -> Reservation:
    reservation: Reservation = generics.get_object_or_404(Reservation.objects.all(), pk=pk)
    return reservation


class ReservationListView(ReservationView, generics.ListCreateAPIView[Reservation]):
    """`?tab=drafts|awaiting_deposit|confirmed|ongoing|closed|cancelled`, `?kind=`, `?owner=`,
    `?client=`, `?from=&to=` (event dates), `?search=`."""

    pagination_class = None

    def get_serializer_class(self) -> Any:
        return ReservationSerializer if self.request.method == "POST" else ReservationListSerializer

    def get_queryset(self) -> QuerySet[Reservation]:
        if getattr(self, "swagger_fake_view", False):
            return Reservation.all_tenants.none()
        return selectors.filter_list(selectors.with_money(), self.request.query_params)

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = ReservationSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        lines = line_inputs(data.pop("lines"))
        reservation = services.create_reservation(
            data, lines, user=request.user  # type: ignore[arg-type]
        )
        response = _detail(request, reservation.pk)
        response.status_code = status.HTTP_201_CREATED
        return response


class ReservationDetailView(ReservationView, APIView):
    @extend_schema(responses=ReservationSerializer)
    def get(self, request: Request, pk: str) -> Response:
        _get(pk)
        return _detail(request, pk)

    @extend_schema(request=ReservationSerializer, responses=ReservationSerializer)
    def patch(self, request: Request, pk: str) -> Response:
        reservation = _get(pk)
        serializer = ReservationSerializer(
            reservation, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        lines = line_inputs(data.pop("lines")) if "lines" in data else None
        services.update_reservation(
            reservation, data, lines, user=request.user  # type: ignore[arg-type]
        )
        return _detail(request, pk)


class ActionView(ReservationView, APIView):
    write_roles = EDIT


class ConfirmView(ActionView):
    @extend_schema(request=None, responses=ReservationSerializer)
    def post(self, request: Request, pk: str) -> Response:
        services.confirm(_get(pk), user=request.user)  # type: ignore[arg-type]
        return _detail(request, pk)


class MoveView(ActionView):
    """Drag in the calendar (§4.3): every date shifts, availability checked again."""

    @extend_schema(request=MoveSerializer, responses=ReservationSerializer)
    def post(self, request: Request, pk: str) -> Response:
        serializer = MoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.move(
            _get(pk), days=serializer.validated_data["days"], user=request.user  # type: ignore[arg-type]
        )
        return _detail(request, pk)


class StatusView(ActionView):
    """Logistic steps without stock operation (préparation, installée, en cours, récupérée)."""

    write_roles = LOGISTICS

    @extend_schema(request=StatusSerializer, responses=ReservationSerializer)
    def post(self, request: Request, pk: str) -> Response:
        serializer = StatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target = serializer.validated_data["status"]
        if target == Reservation.Status.QUOTE_SENT and role_of(request) not in EDIT:
            raise BusinessError(
                "forbidden", "Votre rôle ne permet pas cette action.", status_code=403
            )
        services.advance(_get(pk), target, user=request.user)  # type: ignore[arg-type]
        return _detail(request, pk)


class CheckoutView(ActionView):
    write_roles = LOGISTICS

    @extend_schema(request=CheckoutSerializer, responses=ReservationSerializer)
    def post(self, request: Request, pk: str) -> Response:
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.checkout(
            _get(pk), serializer.validated_data["quantities"], user=request.user  # type: ignore[arg-type]
        )
        return _detail(request, pk)


class ReturnView(ActionView):
    write_roles = LOGISTICS

    @extend_schema(request=ReturnSerializer, responses=ReservationSerializer)
    def post(self, request: Request, pk: str) -> Response:
        serializer = ReturnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        counts = {
            line_id: services.ReturnInput(**values)
            for line_id, values in serializer.validated_data["lines"].items()
        }
        services.process_return(_get(pk), counts, user=request.user)  # type: ignore[arg-type]
        return _detail(request, pk)


class CancelView(ActionView):
    @extend_schema(request=CancelSerializer, responses=ReservationSerializer)
    def post(self, request: Request, pk: str) -> Response:
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.cancel(
            _get(pk),
            reason=serializer.validated_data["reason"],
            user=request.user,  # type: ignore[arg-type]
            request=request,
        )
        return _detail(request, pk)


class PaymentView(ActionView):
    write_roles = PAYMENTS

    @extend_schema(request=PaymentInputSerializer, responses=ReservationSerializer)
    def post(self, request: Request, pk: str) -> Response:
        serializer = PaymentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.record_payment(
            _get(pk),
            user=request.user,  # type: ignore[arg-type]
            request=request,
            **serializer.validated_data,
        )
        response = _detail(request, pk)
        response.status_code = status.HTTP_201_CREATED
        return response


class SecurityView(ActionView):
    write_roles = PAYMENTS

    @extend_schema(request=SecuritySerializer, responses=ReservationSerializer)
    def post(self, request: Request, pk: str) -> Response:
        serializer = SecuritySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.settle_security(
            _get(pk), user=request.user, **serializer.validated_data  # type: ignore[arg-type]
        )
        return _detail(request, pk)


class PaymentCancelView(ReservationView, APIView):
    write_roles = PAYMENTS

    @extend_schema(request=CancelSerializer, responses=PaymentSerializer)
    def post(self, request: Request, pk: str) -> Response:
        payment = generics.get_object_or_404(ReservationPayment.objects.all(), pk=pk)
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.cancel_payment(
            payment,
            reason=serializer.validated_data["reason"],
            user=request.user,  # type: ignore[arg-type]
            request=request,
        )
        payment.refresh_from_db()
        return Response(PaymentSerializer(payment).data)


class ShortageView(ReservationView, APIView):
    """What the reservation lacks over its period, with equivalent items to suggest (§4.2)."""

    @extend_schema(responses={200: OpenApiResponse(OpenApiTypes.OBJECT)})
    def get(self, request: Request, pk: str) -> Response:
        reservation = _get(pk)
        first, last = services.period(reservation)
        costs = can_see_margins(role_of(request))
        rows = []
        for s in services.shortages(reservation):
            line = (
                reservation.lines.filter(kind=ReservationLine.Kind.RENTAL, item=s.item)
                .order_by("position")
                .first()
            )
            rows.append(
                {
                    "item": str(s.item.pk),
                    "name": s.item.name,
                    "needed": s.needed,
                    "available": s.available,
                    "alternatives": services.alternatives(s, first, last),
                    # Complete at a partner (feedback 14/11/2026): the rental line to split,
                    # and what each partner can still lend over the period.
                    "line": str(line.pk) if line else None,
                    "partner_quantity": line.partner_quantity if line else 0,
                    "partners": [
                        {
                            "supply": str(offer.supply.pk),
                            "vendor": str(offer.supply.vendor_id),
                            "vendor_name": offer.supply.vendor.name,
                            "free": offer.free,
                            "unit_cost": offer.supply.unit_cost if costs else None,
                        }
                        for offer in partners.offers(
                            s.item, first, last, exclude=str(reservation.pk)
                        )
                        if offer.free > 0 or (line and line.partner_supply_id == offer.supply.pk)
                    ],
                }
            )
        return Response(rows)


class DocumentView(ReservationView, APIView):
    """`?type=checkout|return`: « bon de sortie » or « bon de retour » (PDF, agency identity);
    `?type=partner&vendor=<id>`: the order to send that partner (feedback 14/11/2026)."""

    @extend_schema(
        parameters=[
            OpenApiParameter("type", enum=["checkout", "return", "partner"]),
            OpenApiParameter("vendor", str),
        ],
        responses={(200, "application/pdf"): bytes},
    )
    def get(self, request: Request, pk: str) -> HttpResponse:
        reservation = _get(pk)
        kind = request.query_params.get("type", "checkout")
        if kind not in ("checkout", "return", "partner"):
            raise BusinessError("invalid", "Document inconnu.")
        if kind == "partner":
            vendor = request.query_params.get("vendor", "")
            pdf = documents.render_partner_order(
                reservation, vendor, costs=can_see_margins(role_of(request))
            )
            response = HttpResponse(pdf, content_type="application/pdf")
            response["Content-Disposition"] = (
                f'inline; filename="commande-partenaire-{reservation.number}.pdf"'
            )
            return response
        pdf = documents.render(reservation, kind)
        response = HttpResponse(pdf, content_type="application/pdf")
        name = "bon-de-sortie" if kind == "checkout" else "bon-de-retour"
        response["Content-Disposition"] = f'inline; filename="{name}-{reservation.number}.pdf"'
        return response


class StatsView(ReservationView, APIView):
    @extend_schema(responses={200: OpenApiResponse(OpenApiTypes.OBJECT)})
    def get(self, request: Request) -> Response:
        data = selectors.stats()
        if not can_see_balances(role_of(request)):
            data["balance_due"] = None
            data["awaiting_deposit_amount"] = None
        return Response(data)


class ExportView(ReservationView, APIView):
    """« Exporter » (§4.2): the filtered list as CSV or Excel (amounts by role)."""

    @extend_schema(
        parameters=[OpenApiParameter("type", enum=["csv", "xlsx"])],
        responses={(200, "application/octet-stream"): bytes},
    )
    def get(self, request: Request) -> HttpResponse:
        fmt = request.query_params.get("type", "csv")
        if fmt not in ("csv", "xlsx"):
            raise BusinessError("invalid", "Format inconnu : csv ou xlsx.")
        money = can_see_balances(role_of(request))
        rows = selectors.filter_list(selectors.with_money(), request.query_params)
        header = ["Numéro", "Client", "Événement", "Début", "Statut"]
        if money:
            header += ["Montant", "Payé", "Solde"]
        table = [header]
        for r in rows:
            line: list[Any] = [
                r.number,
                r.client.name,
                r.title,
                timezone.localtime(r.event_start).strftime("%d/%m/%Y %H:%M"),
                r.get_status_display(),
            ]
            if money:
                line += [r.total, r.paid, r.balance]  # type: ignore[attr-defined]
            table.append(line)
        organization = require_current_organization()
        stamp = timezone.localdate().isoformat()
        if fmt == "csv":
            buffer = io.StringIO()
            csv.writer(buffer, delimiter=";").writerows(table)
            response = HttpResponse("﻿" + buffer.getvalue(), content_type="text/csv; charset=utf-8")
        else:
            from openpyxl import Workbook

            workbook = Workbook()
            sheet = workbook.active
            assert sheet is not None
            sheet.title = "Réservations"
            for row in table:
                sheet.append(row)
            output = io.BytesIO()
            workbook.save(output)
            response = HttpResponse(
                output.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        response["Content-Disposition"] = (
            f'attachment; filename="reservations-{organization.slug}-{stamp}.{fmt}"'
        )
        audit.record(
            "reservations.exported", organization, request=request, changes={"format": fmt}
        )
        return response


class PartnerLineView(ActionView):
    """Take part of a rental line from a partner (feedback 14/11/2026). `quantity` 0 or no
    `supply`: everything comes from our stock again."""

    @extend_schema(request=PartnerAssignSerializer, responses=ReservationSerializer)
    def post(self, request: Request, pk: str, line: str) -> Response:
        reservation = _get(pk)
        target = generics.get_object_or_404(reservation.lines.all(), pk=line)
        serializer = PartnerAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        partners.assign(
            reservation,
            target,
            serializer.validated_data["supply"],
            serializer.validated_data["quantity"],
            user=request.user,  # type: ignore[arg-type]
        )
        return _detail(request, pk)


class PartnerOrdersView(ReservationView, APIView):
    """One order per partner: what to ask for, and (owner, accountant) what it costs."""

    @extend_schema(responses={200: OpenApiResponse(OpenApiTypes.OBJECT)})
    def get(self, request: Request, pk: str) -> Response:
        orders = partners.orders(_get(pk))
        if not can_see_margins(role_of(request)):
            for order in orders:
                order["total"] = None
                for row in order["lines"]:
                    row["unit_cost"] = row["total"] = None
        return Response(orders)
