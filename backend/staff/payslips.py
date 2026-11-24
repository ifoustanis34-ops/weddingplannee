"""Pay slips (feedback 24/11/2026): « Bulletin de paie » of the month and « Fiche de paie
journalière » of a day paid on the spot, one per person, alone or all together in one PDF, and
the agency's « Réglages de la paie ». Owner and accountant only (`pay_view`)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import QuerySet
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core import audit
from core.exceptions import BusinessError
from core.tenant import require_current_organization
from documents import rendering
from documents import services as branding_services
from documents.quote_document import long_date, money
from organizations.timezones import org_tz
from reservations.models import Reservation

from . import services
from .models import (
    Assignment,
    Attendance,
    PayLine,
    PayPeriod,
    PayrollSettings,
    StaffMember,
    StaffPayment,
)
from .views import METHOD_LABELS, PERMISSIONS, Role, role_of

TAX_LABELS = {
    "niu": "NIU",
    "rccm": "RCCM",
    "nif": "NIF",
    "ncc": "NCC",
    "ninea": "NINEA",
    "ifu": "IFU",
}


def _fonts() -> dict[str, str]:
    return {
        "m400": rendering.asset_url("fonts/montserrat-latin-400-normal.woff"),
        "m700": rendering.asset_url("fonts/montserrat-latin-700-normal.woff"),
    }


def _employer() -> dict[str, Any]:
    organization = require_current_organization()
    branding = branding_services.get_branding()
    settings = services.get_payroll_settings()
    return {
        "name": branding.legal_name or branding.trade_name or organization.name,
        "trade_name": branding.trade_name or organization.name,
        "logo": branding_services.logo_data_uri(),
        "address": branding.address,
        "phone": (branding.phones or [""])[0],
        "ids": [
            f"{TAX_LABELS.get(key, key.upper())} {value}"
            for key, value in (branding.tax_ids or {}).items()
            if value
        ]
        + ([f"CNPS employeur {settings.employer_cnps}"] if settings.employer_cnps else []),
        "signatory": settings.signatory,
        "contributions": settings.contributions_enabled,
    }


def _pdf(template: str, context: dict[str, Any], filename: str) -> HttpResponse:
    organization = require_current_organization()
    html = render_to_string(template, {**context, "fonts": _fonts()})
    response = HttpResponse(
        rendering.html_to_pdf(html, str(organization.pk)), content_type="application/pdf"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _slug(text: str) -> str:
    import unicodedata

    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return "-".join("".join(c if c.isalnum() else " " for c in plain).split()) or "personnel"


def _amounts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**item, "money": money(int(item["amount"]))} for item in items]


# --- Monthly slip ---------------------------------------------------------------------------------


def _slip_context(line: PayLine, number: int) -> dict[str, Any]:
    period, staff = line.period, line.staff
    slip = line.slip or {}
    services.ensure_employee_number(staff)
    attendances = Attendance.objects.filter(
        staff=staff, date__range=(period.start, period.end)
    ).select_related("assignment__reservation")
    cumul = services.year_to_date(line)
    unit = {
        "monthly": "mois",
        "daily": "jours",
        "mission": "missions",
        "hourly": "heures",
    }[staff.pay_mode]
    quantity = {
        "monthly": None,
        "daily": line.days,
        "mission": line.missions,
        "hourly": f"{line.hours:.2f}".replace(".", ","),
    }[staff.pay_mode]
    return {
        "number": f"BP-{period.start:%Y%m}-{number:03d}",
        "period": (
            f"Du {long_date(period.start.isoformat())} au {long_date(period.end.isoformat())}"
        ),
        "month": f"{period.start:%m/%Y}",
        "staff": staff,
        "hire_date": long_date(staff.hire_date.isoformat()) if staff.hire_date else "—",
        "base_label": f"Salaire de base ({staff.get_pay_mode_display().lower()})",
        "base_detail": (
            f"{quantity} {unit} × {money(staff.pay_rate)}"
            if quantity is not None
            else money(staff.pay_rate)
        ),
        "base": money(line.base),
        "gains": _amounts([i for i in line.items or [] if i["kind"] == "gain"]),
        "deductions": _amounts([i for i in line.items or [] if i["kind"] == "deduction"]),
        "gross": money(line.gross),
        "taxable": money(int(slip.get("taxable", line.gross))),
        "employee": [
            {**c, "money": money(int(c["amount"])), "base_money": money(int(c["base"]))}
            for c in slip.get("employee", [])
        ],
        "employer": [
            {**c, "money": money(int(c["amount"])), "base_money": money(int(c["base"]))}
            for c in slip.get("employer", [])
        ],
        "withheld": money(int(slip.get("withheld", 0))),
        "employer_total": money(int(slip.get("employer_total", 0))),
        "net": money(line.net),
        "already_paid": money(line.already_paid) if line.already_paid else None,
        "to_pay": money(line.total),
        "paid": (
            f"Payé le {long_date(line.paid_at.isoformat())}"
            + (f" · {METHOD_LABELS.get(line.method, line.method)}" if line.method else "")
            if line.paid_at
            else None
        ),
        "days": line.days,
        "missions": line.missions,
        "hours": f"{line.hours:.2f}".replace(".", ",").removesuffix(",00"),
        "absences": sum(1 for a in attendances if a.status == Attendance.Status.ABSENT),
        "cumul": {key: money(value) for key, value in cumul.items()},
        "draft": period.status == PayPeriod.Status.DRAFT,
    }


def _lines(period: PayPeriod) -> list[PayLine]:
    return list(period.lines.select_related("staff", "period").order_by("staff__full_name"))


class PayslipView(APIView):
    """GET `/pay-lines/{id}/statement`: the « Bulletin de paie » of one person."""

    permission_classes = PERMISSIONS
    pay_view = True

    @extend_schema(responses={200: OpenApiResponse(description="PDF")})
    def get(self, request: Request, pk: str) -> HttpResponse:
        line: PayLine = generics.get_object_or_404(
            PayLine.objects.select_related("period", "staff"), pk=pk
        )
        order = [item.pk for item in _lines(line.period)]
        slip = _slip_context(line, order.index(line.pk) + 1)
        return _pdf(
            "staff/payslip.html",
            {"employer": _employer(), "slips": [slip]},
            f"bulletin-{_slug(line.staff.full_name)}-{line.period.start:%Y-%m}.pdf",
        )


class PeriodPayslipsView(APIView):
    """GET `/pay-periods/{id}/payslips`: every slip of the period, one per page."""

    permission_classes = PERMISSIONS
    pay_view = True

    @extend_schema(responses={200: OpenApiResponse(description="PDF")})
    def get(self, request: Request, pk: str) -> HttpResponse:
        period: PayPeriod = generics.get_object_or_404(PayPeriod.objects.all(), pk=pk)
        lines = _lines(period)
        if not lines:
            raise BusinessError(
                "not_found", "Aucune ligne de paie sur cette période.", status_code=404
            )
        return _pdf(
            "staff/payslip.html",
            {
                "employer": _employer(),
                "slips": [_slip_context(line, i + 1) for i, line in enumerate(lines)],
            },
            f"bulletins-{period.start:%Y-%m}.pdf",
        )


# --- Daily slip -----------------------------------------------------------------------------------


def _day_slip(payment: StaffPayment) -> dict[str, Any]:
    staff = payment.staff
    services.ensure_employee_number(staff)
    tz = org_tz(require_current_organization())
    first = datetime.combine(payment.date, time.min, tzinfo=tz)
    assignments = (
        Assignment.objects.filter(staff=staff, start__lt=first + timedelta(days=1), end__gt=first)
        .exclude(reservation__status="cancelled")
        .select_related("reservation", "attendance")
    )
    if payment.reservation_id:
        assignments = assignments.filter(reservation_id=payment.reservation_id)
    missions = []
    for assignment in assignments:
        attendance = getattr(assignment, "attendance", None)
        local = timezone.localtime
        missions.append(
            {
                "event": f"{assignment.reservation.number} · {assignment.reservation.title}",
                "step": assignment.get_step_display(),
                "role": assignment.role,
                "arrival": (
                    local(attendance.check_in, tz).strftime("%H:%M")
                    if attendance is not None and attendance.check_in
                    else "—"
                ),
                "departure": (
                    local(attendance.check_out, tz).strftime("%H:%M")
                    if attendance is not None and attendance.check_out
                    else "—"
                ),
                "status": attendance.get_status_display() if attendance is not None else "Prévu",
            }
        )
    items = payment.items or []
    worked = [getattr(a, "attendance", None) for a in assignments]
    hours = payment.hours or sum((a.hours for a in worked if a is not None), Decimal(0))
    return {
        "number": f"FJ-{payment.date:%Y%m%d}-{str(payment.pk)[:4].upper()}",
        "date": long_date(payment.date.isoformat()),
        "staff": staff,
        "missions": missions,
        "hours": f"{hours:.2f}".replace(".", ",").removesuffix(",00") if hours else "—",
        "rate": money(staff.pay_rate),
        "mode": staff.get_pay_mode_display(),
        "base": money(payment.base or payment.amount),
        "gains": _amounts([i for i in items if i["kind"] == "gain"]),
        "deductions": _amounts([i for i in items if i["kind"] == "deduction"]),
        "net": money(payment.amount),
        "method": METHOD_LABELS.get(payment.method, payment.method),
        "mobile_money": (
            staff.mobile_money if payment.method in ("orange_money", "mtn_momo", "wave") else ""
        ),
        "note": payment.note,
    }


def _payments() -> QuerySet[StaffPayment]:
    return StaffPayment.objects.select_related("staff", "reservation")


class PaymentSlipView(APIView):
    """GET `/staff-payments/{id}/slip`: « Fiche de paie journalière » of one person."""

    permission_classes = PERMISSIONS
    pay_view = True

    @extend_schema(responses={200: OpenApiResponse(description="PDF")})
    def get(self, request: Request, pk: str) -> HttpResponse:
        payment: StaffPayment = generics.get_object_or_404(_payments(), pk=pk)
        return _pdf(
            "staff/day_slip.html",
            {"employer": _employer(), "slips": [_day_slip(payment)]},
            f"fiche-journaliere-{_slug(payment.staff.full_name)}-{payment.date.isoformat()}.pdf",
        )


class DaySlipsView(APIView):
    """GET `/pay/day/slips?date=&reservation=`: every daily slip of that day, one per page."""

    permission_classes = PERMISSIONS
    pay_view = True

    @extend_schema(responses={200: OpenApiResponse(description="PDF")})
    def get(self, request: Request) -> HttpResponse:
        try:
            day = date.fromisoformat(
                request.query_params.get("date") or services.today().isoformat()
            )
        except ValueError as exc:
            raise BusinessError("invalid", "Date illisible (AAAA-MM-JJ).") from exc
        payments = _payments().filter(date=day)
        if request.query_params.get("reservation"):
            reservation = generics.get_object_or_404(
                Reservation.objects.all(), pk=request.query_params["reservation"]
            )
            payments = payments.filter(reservation=reservation)
        payments = payments.order_by("staff__full_name", "created_at")
        if not payments:
            raise BusinessError(
                "not_found",
                "Aucun paiement enregistré ce jour-là : payez d’abord la journée.",
                status_code=404,
            )
        return _pdf(
            "staff/day_slip.html",
            {"employer": _employer(), "slips": [_day_slip(p) for p in payments]},
            f"fiches-journalieres-{day.isoformat()}.pdf",
        )


# --- Settings -------------------------------------------------------------------------------------


class PayrollSettingsSerializer(serializers.ModelSerializer[PayrollSettings]):
    accident_rate = serializers.DecimalField(
        max_digits=4,
        decimal_places=2,
        min_value=Decimal("0"),
        max_value=Decimal("10"),
        coerce_to_string=False,
    )

    class Meta:
        model = PayrollSettings
        fields = ["contributions_enabled", "employer_cnps", "accident_rate", "signatory"]


class PayrollSettingsView(APIView):
    """GET (owner, accountant) · PATCH (owner): « Réglages de la paie ». Turning the
    contributions on or off recomputes the periods still « En cours »."""

    permission_classes = PERMISSIONS
    pay_view = True

    @extend_schema(responses=PayrollSettingsSerializer)
    def get(self, request: Request) -> Response:
        return Response(PayrollSettingsSerializer(services.get_payroll_settings()).data)

    @extend_schema(request=PayrollSettingsSerializer, responses=PayrollSettingsSerializer)
    def patch(self, request: Request) -> Response:
        if role_of(request) != Role.OWNER:
            raise BusinessError("forbidden", "Seul le propriétaire règle la paie.", status_code=403)
        settings = services.get_payroll_settings()
        serializer = PayrollSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        audit.record("payroll.settings", settings, request=request, changes=dict(request.data))
        for period in PayPeriod.objects.filter(status=PayPeriod.Status.DRAFT):
            services.refresh(period)
        return Response(serializer.data)


# --- Salary from the pay screen -------------------------------------------------------------------


class SalarySerializer(serializers.Serializer[Any]):
    pay_mode = serializers.ChoiceField(choices=StaffMember.PayMode.choices, required=False)
    pay_rate = serializers.IntegerField(min_value=0, required=False)
    declared = serializers.BooleanField(required=False)
    cnps_number = serializers.CharField(max_length=32, required=False, allow_blank=True)


class SalaryView(APIView):
    """PATCH `/staff/{id}/salary` (owner, accountant): the salary set from « Salaires du mois »
    (feedback 24/11/2026: « je ne vois pas où mettre le salaire »). Audited."""

    permission_classes = PERMISSIONS
    pay_view = True

    @extend_schema(request=SalarySerializer, responses={200: OpenApiResponse()})
    def patch(self, request: Request, pk: str) -> Response:
        staff: StaffMember = generics.get_object_or_404(
            StaffMember.objects.filter(is_deleted=False), pk=pk
        )
        data = SalarySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        before = {"pay_mode": staff.pay_mode, "pay_rate": staff.pay_rate}
        for field, value in data.validated_data.items():
            setattr(staff, field, value)
        staff.save()
        audit.record(
            "staff.salary",
            staff,
            request=request,
            changes={"before": before, **data.validated_data},
        )
        for period in PayPeriod.objects.filter(status=PayPeriod.Status.DRAFT):
            services.refresh(period)
        return Response(
            {
                "pay_mode": staff.pay_mode,
                "pay_rate": staff.pay_rate,
                "declared": staff.declared,
                "cnps_number": staff.cnps_number,
            }
        )
