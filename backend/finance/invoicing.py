"""Invoices and credit notes (docs/specs/reservations-stock.md §6.3).

Chain: quote → deposit invoice → final invoice(s) → receipts, with credit notes when a
reservation is cancelled. Numbers have no gap, per document type and per year (`FA-`, `AV-`,
reserved inside the creating transaction). An invoice is frozen at issue: its lines and its
document snapshot never change; only a credit note cancels it, in whole or in part.

What an invoice has received is not stored: the reservation's payments are allocated to its
invoices in issue order (net of credit notes), so recording or cancelling a payment always
leaves consistent statuses.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from accounts.models import User
from core import audit
from core.exceptions import BusinessError
from core.tenant import require_current_organization
from organizations.models import DocumentSequence
from organizations.numbering import next_number
from organizations.timezones import org_tz

from . import invoice_documents as documents
from .models import CreditNote, Invoice, InvoiceLine, RevenueCategory
from .revenues import CATEGORY_OF_LINE

PAYMENT_DAYS = 7  # an invoice is due a week after issue, the balance a week before the event
METHODS_TEXT = "Espèces, virement, Orange Money, MTN MoMo, Wave ou chèque."


def _today() -> date:
    return timezone.now().astimezone(org_tz(require_current_organization())).date()


def credited(invoice: Invoice) -> int:
    return int(invoice.credit_notes.aggregate(total=Sum("amount"))["total"] or 0)


def invoiced(reservation: Any) -> int:
    """What the reservation's live invoices still claim (credit notes deducted)."""
    total = Invoice.objects.filter(reservation=reservation).aggregate(total=Sum("total"))["total"]
    credits = CreditNote.objects.filter(reservation=reservation).aggregate(total=Sum("amount"))[
        "total"
    ]
    return int(total or 0) - int(credits or 0)


# --- Status --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class InvoiceState:
    net: int  # total − credit notes
    paid: int
    balance: int
    status: str  # paid, partial, issued, overdue, cancelled


def states(invoices: list[Invoice], today: date | None = None) -> dict[str, InvoiceState]:
    """Payments of each reservation allocated to its invoices, oldest first."""
    from reservations.services import paid as reservation_paid

    today = today or _today()
    result: dict[str, InvoiceState] = {}
    reservations = {invoice.reservation_id for invoice in invoices}
    for reservation_id in reservations:
        siblings = list(
            Invoice.objects.filter(reservation_id=reservation_id)
            .annotate(credited_total=Sum("credit_notes__amount"))
            .order_by("issued_at", "number")
        )
        left = reservation_paid(siblings[0].reservation) if siblings else 0
        for invoice in siblings:
            net = invoice.total - int(invoice.credited_total or 0)
            paid = min(net, max(0, left))
            left -= paid
            balance = net - paid
            if net <= 0:
                status = "cancelled"
            elif balance == 0:
                status = "paid"
            elif invoice.due_at < today:
                status = "overdue"
            elif paid:
                status = "partial"
            else:
                status = "issued"
            result[str(invoice.pk)] = InvoiceState(net, paid, balance, status)
    return result


# --- Issue ---------------------------------------------------------------------------------------


def _event_day(reservation: Any) -> date:
    return timezone.localtime(
        reservation.event_start, org_tz(require_current_organization())
    ).date()


@transaction.atomic
def issue(reservation: Any, kind: str, *, user: User, request: Any = None) -> Invoice:
    """Deposit invoice (the deposit not invoiced yet) or final invoice (all that is not)."""
    from reservations.models import Reservation

    reservation = (
        Reservation.objects.select_for_update().select_related("client").get(pk=reservation.pk)
    )
    if reservation.status in (Reservation.Status.DRAFT, Reservation.Status.CANCELLED):
        raise BusinessError(
            "invalid", "Confirmez la réservation (ou envoyez son devis) avant de la facturer."
        )
    today = _today()
    already = invoiced(reservation)
    lines: list[dict[str, Any]] = []
    if kind == Invoice.Kind.DEPOSIT:
        if Invoice.objects.filter(reservation=reservation).exists():
            raise BusinessError("invalid", "Cette réservation a déjà une facture.")
        amount = reservation.deposit_required
        if amount <= 0:
            raise BusinessError("invalid", "Aucun acompte n’est demandé sur cette réservation.")
        pct = round(amount * 100 / reservation.total) if reservation.total else 0
        lines.append(
            {
                "label": f"Acompte de {pct} % — {reservation.title}",
                "quantity": 1,
                "unit_price": amount,
                "amount": amount,
                "category": "",
            }
        )
        due = today + timedelta(days=PAYMENT_DAYS)
    elif kind == Invoice.Kind.FINAL:
        amount = reservation.total - already
        if amount <= 0:
            raise BusinessError("invalid", "Tout est déjà facturé sur cette réservation.")
        lines += [
            {
                "label": line.label,
                "quantity": line.quantity,
                "unit_price": line.unit_price,
                "amount": line.amount,
                "category": CATEGORY_OF_LINE.get(line.kind, RevenueCategory.SERVICE),
            }
            for line in reservation.lines.all().order_by("position", "created_at")
        ]
        if reservation.discount:
            lines.append(
                _fee("Remise commerciale", -min(reservation.discount, reservation.subtotal))
            )
        if reservation.transport_fee:
            lines.append(_fee("Transport", reservation.transport_fee, RevenueCategory.TRANSPORT))
        if reservation.setup_fee:
            lines.append(_fee("Installation", reservation.setup_fee, RevenueCategory.SERVICE))
        for previous in Invoice.objects.filter(reservation=reservation).order_by("issued_at"):
            net = previous.total - credited(previous)
            if net:
                lines.append(_fee(f"Déjà facturé — {previous.number}", -net))
        if sum(line["amount"] for line in lines) != amount:  # defensive: never a wrong total
            lines.append(_fee("Ajustement", amount - sum(line["amount"] for line in lines)))
        due = max(today + timedelta(days=PAYMENT_DAYS), _event_day(reservation) - timedelta(7))
    else:
        raise BusinessError("invalid", "Type de facture inconnu.")

    invoice: Invoice = Invoice.objects.create(
        number=next_number(DocumentSequence.Kind.INVOICE),
        kind=kind,
        reservation=reservation,
        client=reservation.client,
        issued_at=today,
        due_at=due,
        total=amount,
        created_by=user,
    )
    InvoiceLine.objects.bulk_create(
        InvoiceLine(organization=invoice.organization, invoice=invoice, position=index, **line)
        for index, line in enumerate(lines)
    )
    invoice.snapshot = documents.invoice_snapshot(invoice)
    invoice.save(update_fields=["snapshot", "updated_at"])
    audit.record("invoice.issued", invoice, request=request, changes={"total": amount})
    return invoice


def _fee(label: str, amount: int, category: str = "") -> dict[str, Any]:
    return {
        "label": label,
        "quantity": 1,
        "unit_price": amount,
        "amount": amount,
        "category": category,
    }


@transaction.atomic
def credit(
    invoice: Invoice, *, amount: int, reason: str, user: User | None, request: Any = None
) -> CreditNote:
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    reason = reason.strip()
    if not reason:
        raise BusinessError(
            "invalid", "Indiquez le motif de l’avoir.", {"reason": ["Obligatoire."]}
        )
    left = invoice.total - credited(invoice)
    if amount <= 0 or amount > left:
        raise BusinessError(
            "invalid",
            f"L’avoir doit être compris entre 1 et {left:,} FCFA.".replace(",", " "),
            {"amount": [f"Maximum {left}"]},
        )
    note: CreditNote = CreditNote.objects.create(
        number=next_number(DocumentSequence.Kind.CREDIT_NOTE),
        invoice=invoice,
        reservation=invoice.reservation,
        client=invoice.client,
        issued_at=_today(),
        amount=amount,
        reason=reason,
        created_by=user,
    )
    note.snapshot = documents.credit_note_snapshot(note)
    note.save(update_fields=["snapshot", "updated_at"])
    audit.record(
        "credit_note.issued",
        note,
        request=request,
        changes={"invoice": invoice.number, "amount": amount},
    )
    return note


def on_reservation_cancelled(reservation: Any, *, kept: int, user: User | None) -> list[CreditNote]:
    """Credit notes for what the client no longer owes: everything invoiced except the deposit
    the agency keeps (its policy), deposit invoice first."""
    notes = []
    keep = kept
    for invoice in Invoice.objects.filter(reservation=reservation).order_by("issued_at", "number"):
        creditable = invoice.total - credited(invoice)
        kept_here = min(keep, creditable)
        keep -= kept_here
        if creditable - kept_here > 0:
            notes.append(
                credit(
                    invoice,
                    amount=creditable - kept_here,
                    reason=f"Annulation de la réservation {reservation.number}",
                    user=user,
                )
            )
    return notes
