"""API of invoices, credit notes, revenues, treasury and expense receipts (§6.1–§6.3).

Reading: the roles that see balances (owner, accountant, planner). Issuing an invoice or a
credit note: owner and accountant (FinancePermission). Treasury shows expenses: owner and
accountant only (`margins_only`).
"""

from __future__ import annotations

from typing import Any

from django.db.models import Q, QuerySet
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, serializers, status
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core import audit
from core.exceptions import BusinessError
from core.fields import TenantPrimaryKeyRelatedField
from core.permissions import IsTenantMember
from core.signed_files import signed_url
from core.tenant import require_current_organization
from documents import images
from organizations.timezones import org_tz
from reservations.models import Reservation

from . import invoice_documents, invoicing, profitability, reports, treasury
from .models import CreditNote, Expense, Invoice, Revenue
from .periods import PERIODS, from_params
from .permissions import FinancePermission

PERMISSIONS = [IsTenantMember, FinancePermission]
RECEIPT_MAX = 8 * 1024 * 1024


def _today() -> Any:
    return timezone.now().astimezone(org_tz(require_current_organization())).date()


# --- Serializers ---------------------------------------------------------------------------------


class CreditNoteSerializer(serializers.ModelSerializer[CreditNote]):
    invoice_number = serializers.CharField(source="invoice.number", read_only=True)
    reservation_number = serializers.CharField(source="reservation.number", read_only=True)
    client_name = serializers.CharField(source="client.name", read_only=True)

    class Meta:
        model = CreditNote
        fields = [
            "id",
            "number",
            "invoice",
            "invoice_number",
            "reservation",
            "reservation_number",
            "client_name",
            "issued_at",
            "amount",
            "reason",
        ]
        read_only_fields = fields


class InvoiceSerializer(serializers.ModelSerializer[Invoice]):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    reservation_detail = serializers.SerializerMethodField()
    client_detail = serializers.SerializerMethodField()
    lines = serializers.SerializerMethodField()
    credit_notes = CreditNoteSerializer(many=True, read_only=True)
    credited = serializers.SerializerMethodField()
    paid = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            "id",
            "number",
            "kind",
            "kind_label",
            "reservation",
            "reservation_detail",
            "client_detail",
            "issued_at",
            "due_at",
            "total",
            "credited",
            "paid",
            "balance",
            "status",
            "lines",
            "credit_notes",
        ]
        read_only_fields = fields

    def _state(self, invoice: Invoice) -> invoicing.InvoiceState:
        states: dict[str, invoicing.InvoiceState] = self.context["states"]
        return states[str(invoice.pk)]

    def get_reservation_detail(self, invoice: Invoice) -> dict[str, str]:
        r = invoice.reservation
        return {"id": str(r.pk), "number": r.number, "title": r.title}

    def get_client_detail(self, invoice: Invoice) -> dict[str, str]:
        return {"id": str(invoice.client_id), "name": invoice.client.name}

    def get_lines(self, invoice: Invoice) -> list[dict[str, Any]]:
        return [
            {
                "label": line.label,
                "quantity": line.quantity,
                "unit_price": line.unit_price,
                "amount": line.amount,
            }
            for line in invoice.lines.all()
        ]

    def get_credited(self, invoice: Invoice) -> int:
        return invoice.total - self._state(invoice).net

    def get_paid(self, invoice: Invoice) -> int:
        return self._state(invoice).paid

    def get_balance(self, invoice: Invoice) -> int:
        return self._state(invoice).balance

    def get_status(self, invoice: Invoice) -> str:
        return self._state(invoice).status


class IssueSerializer(serializers.Serializer[Any]):
    reservation = TenantPrimaryKeyRelatedField(Reservation)
    kind = serializers.ChoiceField(choices=Invoice.Kind.choices)


class CreditSerializer(serializers.Serializer[Any]):
    amount = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=255)


class RevenueSerializer(serializers.ModelSerializer[Revenue]):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    client_name = serializers.CharField(source="client.name", read_only=True, default=None)
    reservation_number = serializers.CharField(
        source="reservation.number", read_only=True, default=None
    )

    class Meta:
        model = Revenue
        fields = [
            "id",
            "date",
            "amount",
            "category",
            "category_label",
            "label",
            "method",
            "client",
            "client_name",
            "reservation",
            "reservation_number",
            "contract",
            "is_cancelled",
        ]
        read_only_fields = fields


# --- Invoices ------------------------------------------------------------------------------------


def _invoices() -> QuerySet[Invoice]:
    return Invoice.objects.select_related("reservation", "client").prefetch_related(
        "lines", "credit_notes__invoice", "credit_notes__reservation", "credit_notes__client"
    )


def _serialize(invoices: list[Invoice]) -> list[dict[str, Any]]:
    states = invoicing.states(invoices)
    return list(InvoiceSerializer(invoices, many=True, context={"states": states}).data)


class InvoiceListView(APIView):
    """`?reservation=&client=&status=paid|partial|issued|overdue|cancelled&search=`."""

    permission_classes = PERMISSIONS

    @extend_schema(responses=InvoiceSerializer(many=True))
    def get(self, request: Request) -> Response:
        params = request.query_params
        invoices = _invoices()
        if params.get("reservation"):
            invoices = invoices.filter(reservation_id=params["reservation"])
        if params.get("client"):
            invoices = invoices.filter(client_id=params["client"])
        if params.get("search"):
            term = params["search"].strip()
            invoices = invoices.filter(
                Q(number__icontains=term)
                | Q(client__name__icontains=term)
                | Q(reservation__number__icontains=term)
            )
        rows = _serialize(list(invoices[:500]))
        if params.get("status"):
            rows = [row for row in rows if row["status"] == params["status"]]
        return Response(rows)

    @extend_schema(request=IssueSerializer, responses=InvoiceSerializer)
    def post(self, request: Request) -> Response:
        serializer = IssueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = invoicing.issue(
            serializer.validated_data["reservation"],
            serializer.validated_data["kind"],
            user=request.user,  # type: ignore[arg-type]
            request=request,
        )
        return Response(_serialize([_invoices().get(pk=invoice.pk)])[0], status=201)


def _invoice(pk: str) -> Invoice:
    invoice: Invoice = generics.get_object_or_404(_invoices(), pk=pk)
    return invoice


class InvoiceDetailView(APIView):
    permission_classes = PERMISSIONS

    @extend_schema(responses=InvoiceSerializer)
    def get(self, request: Request, pk: str) -> Response:
        return Response(_serialize([_invoice(pk)])[0])


def _pdf(snapshot: dict[str, Any], number: str) -> HttpResponse:
    response = HttpResponse(invoice_documents.render_pdf(snapshot), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{invoice_documents.filename(number)}"'
    return response


class InvoicePdfView(APIView):
    permission_classes = PERMISSIONS

    @extend_schema(responses={200: OpenApiResponse(description="PDF")})
    def get(self, request: Request, pk: str) -> HttpResponse:
        invoice = _invoice(pk)
        return _pdf(invoice.snapshot, invoice.number)


class InvoiceCreditView(APIView):
    """« Émettre un avoir » on an invoice (all or part of what it still claims)."""

    permission_classes = PERMISSIONS

    @extend_schema(request=CreditSerializer, responses=CreditNoteSerializer)
    def post(self, request: Request, pk: str) -> Response:
        serializer = CreditSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = invoicing.credit(
            _invoice(pk),
            amount=serializer.validated_data["amount"],
            reason=serializer.validated_data["reason"],
            user=request.user,  # type: ignore[arg-type]
            request=request,
        )
        return Response(CreditNoteSerializer(note).data, status=201)


class CreditNoteListView(generics.ListAPIView[CreditNote]):
    permission_classes = PERMISSIONS
    serializer_class = CreditNoteSerializer
    pagination_class = None

    def get_queryset(self) -> QuerySet[CreditNote]:
        if getattr(self, "swagger_fake_view", False):
            return CreditNote.all_tenants.none()
        notes = CreditNote.objects.select_related("invoice", "reservation", "client")
        if self.request.query_params.get("reservation"):
            notes = notes.filter(reservation_id=self.request.query_params["reservation"])
        return notes


class CreditNotePdfView(APIView):
    permission_classes = PERMISSIONS

    @extend_schema(responses={200: OpenApiResponse(description="PDF")})
    def get(self, request: Request, pk: str) -> HttpResponse:
        note: CreditNote = generics.get_object_or_404(CreditNote.objects.all(), pk=pk)
        return _pdf(note.snapshot, note.number)


# --- Revenues and treasury -----------------------------------------------------------------------


class RevenueListView(APIView):
    """Revenues of a period (`?period=&from=&to=&category=`), newest first."""

    permission_classes = PERMISSIONS

    @extend_schema(
        parameters=[
            OpenApiParameter("period", enum=list(PERIODS), default="month"),
            OpenApiParameter("from", OpenApiTypes.DATE),
            OpenApiParameter("to", OpenApiTypes.DATE),
            OpenApiParameter("category", str),
        ],
        responses=RevenueSerializer(many=True),
    )
    def get(self, request: Request) -> Response:
        period = from_params(request.query_params, _today())
        revenues = Revenue.objects.filter(date__range=(period.start, period.end)).select_related(
            "client", "reservation"
        )
        if request.query_params.get("category"):
            revenues = revenues.filter(category=request.query_params["category"])
        return Response(RevenueSerializer(revenues[:1000], many=True).data)


class TreasuryView(APIView):
    """« Trésorerie »: owner and accountant (it shows the expenses)."""

    permission_classes = PERMISSIONS
    margins_only = True

    @extend_schema(
        parameters=[
            OpenApiParameter("period", enum=list(PERIODS), default="month"),
            OpenApiParameter("from", OpenApiTypes.DATE),
            OpenApiParameter("to", OpenApiTypes.DATE),
        ],
        responses={200: OpenApiResponse(description="Trésorerie de la période")},
    )
    def get(self, request: Request) -> Response:
        today = _today()
        return Response(treasury.compute(from_params(request.query_params, today), today))


# --- Expense receipts ----------------------------------------------------------------------------


class ExpenseReceiptView(APIView):
    """Photo (JPEG, PNG, WebP: resized) or PDF of the receipt, private (§6.2)."""

    permission_classes = PERMISSIONS
    margins_only = True
    parser_classes = [MultiPartParser]

    def _expense(self, pk: str) -> Expense:
        expense: Expense = generics.get_object_or_404(Expense.objects.all(), pk=pk)
        return expense

    @extend_schema(
        request={"multipart/form-data": OpenApiTypes.OBJECT},
        responses={200: OpenApiResponse(description="URL signée du justificatif")},
    )
    def post(self, request: Request, pk: str) -> Response:
        from django.core.files.base import ContentFile

        expense = self._expense(pk)
        upload = request.FILES.get("file")
        if upload is None:
            raise BusinessError(
                "invalid", "Choisissez le justificatif.", {"file": ["Obligatoire."]}
            )
        if upload.size and upload.size > RECEIPT_MAX:
            raise BusinessError("invalid", "Fichier trop lourd : 8 Mo maximum.", {"file": ["8 Mo"]})
        content = upload.read()
        if content.startswith(b"%PDF-"):
            name, data = "receipt.pdf", content
        else:
            if images.sniff(content) == "svg":  # also refuses anything not a real image
                raise BusinessError(
                    "invalid",
                    "Choisissez une photo (JPEG, PNG, WebP) ou un PDF.",
                    {"file": ["Format refusé."]},
                )
            processed = images.process_raster(content, transparent=False)
            name, data = f"receipt.{processed.extension}", processed.content
        if expense.receipt:
            expense.receipt.delete(save=False)
        expense.receipt.save(name, ContentFile(data), save=False)
        expense.save(update_fields=["receipt", "updated_at"])
        return Response({"receipt_url": signed_url(expense.receipt.name)})

    @extend_schema(responses={204: None})
    def delete(self, request: Request, pk: str) -> Response:
        expense = self._expense(pk)
        if expense.receipt:
            expense.receipt.delete(save=False)
            expense.save(update_fields=["receipt", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Profitability and reports (§6.4, §6.5) ------------------------------------------------------

PERIOD_PARAMETERS = [
    OpenApiParameter("period", enum=list(PERIODS), default="month"),
    OpenApiParameter("from", OpenApiTypes.DATE),
    OpenApiParameter("to", OpenApiTypes.DATE),
]


class ProfitabilityView(APIView):
    """`?by=event|service|item` over a period: owner and accountant (margins)."""

    permission_classes = PERMISSIONS
    margins_only = True

    @extend_schema(
        parameters=[
            OpenApiParameter("by", enum=list(profitability.BUILDERS), default="event"),
            *PERIOD_PARAMETERS,
        ],
        responses={200: OpenApiResponse(description="Lignes de rentabilité")},
    )
    def get(self, request: Request) -> Response:
        by = request.query_params.get("by", "event")
        if by not in profitability.BUILDERS:
            raise BusinessError("invalid", "Choisissez event, service ou item.", {"by": [by]})
        period = from_params(request.query_params, _today())
        return Response(
            {
                "by": by,
                "period": {"start": period.start, "end": period.end, "key": period.key},
                "rows": profitability.BUILDERS[by](period),
            }
        )


class ReportView(APIView):
    """`/reports/{type}?period=&from=&to=&output=json|pdf|xlsx` (« output »: `format` is DRF's)."""

    permission_classes = PERMISSIONS
    margins_only = True

    @extend_schema(
        parameters=[
            *PERIOD_PARAMETERS,
            OpenApiParameter("output", enum=["json", "pdf", "xlsx", "csv"], default="json"),
        ],
        responses={200: OpenApiResponse(description="Rapport")},
    )
    def get(self, request: Request, kind: str) -> Response | HttpResponse:
        if kind not in reports.TYPES:
            raise BusinessError("not_found", "Rapport inconnu.", status_code=404)
        period = from_params(request.query_params, _today())
        report = reports.build(kind, period)
        output = request.query_params.get("output", "json")
        name = f"rapport-{kind}-{period.start:%Y%m%d}-{period.end:%Y%m%d}"
        if output not in ("pdf", "xlsx", "csv"):
            return Response(report)
        response = reports.respond(report, output, name)
        audit.record(
            "report.exported",
            require_current_organization(),
            request=request,
            changes={"type": kind, "output": output},
        )
        return response
