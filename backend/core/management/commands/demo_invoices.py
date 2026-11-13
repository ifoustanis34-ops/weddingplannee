"""Demo invoices and direct costs (reservations-stock.md §11 « Finances »): deposit and final
invoices of the demo reservations, exactly 2 overdue at opening; costs attached to each
reservation and one loss-making event (far transport). The credit note comes from the cancelled
reservation (demo_reservations). Idempotent."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from accounts.models import User
from finance import invoice_documents, invoicing
from finance.models import Expense, ExpenseCategory, Invoice
from reservations.commitments import SOLD
from reservations.models import Reservation

FINAL_STATUSES = (
    Reservation.Status.DELIVERED,
    Reservation.Status.INSTALLED,
    Reservation.Status.IN_PROGRESS,
    Reservation.Status.PICKED_UP,
    Reservation.Status.CLOSED,
)


def _backdate(invoice: Invoice, issued: object, due: object) -> None:
    Invoice.objects.filter(pk=invoice.pk).update(issued_at=issued, due_at=due)
    invoice.refresh_from_db()
    invoice.snapshot = invoice_documents.invoice_snapshot(invoice)
    invoice.save(update_fields=["snapshot", "updated_at"])


def _expenses(owner: User) -> None:
    """Direct costs of the reservations (§6.4): fuel, consumables, subcontracting — and the
    loss-making wedding in Yaoundé, whose transport costs more than the order (§11)."""
    transport = ExpenseCategory.objects.get(name="Transport et carburant")
    subcontracting = ExpenseCategory.objects.get(name="Sous-traitance")
    for reservation in Reservation.objects.filter(status__in=SOLD):
        day = timezone.localtime(reservation.event_start).date()
        fuel = max(15_000, reservation.total * 8 // 100 // 1000 * 1000)
        Expense.objects.create(
            label=f"Carburant et péage — {reservation.number}",
            amount=fuel,
            date=day,
            category=transport,
            reservation=reservation,
            supplier="Total Énergies",
            method="cash",
            is_paid=day <= timezone.localdate(),
            created_by=owner,
        )
        if reservation.kind == Reservation.Kind.MIXED:
            Expense.objects.create(
                label=f"Fleurs fraîches et consommables — {reservation.number}",
                amount=reservation.total * 12 // 100 // 1000 * 1000,
                date=day,
                category=subcontracting,
                reservation=reservation,
                supplier="Fleurs d’Ébène",
                method="orange_money",
                is_paid=day <= timezone.localdate(),
                created_by=owner,
            )
    far = (
        Reservation.objects.filter(venue__icontains="Yaoundé", status__in=SOLD)
        .order_by("-event_start")
        .first()
    )
    if far is not None:
        Expense.objects.create(
            label=f"Camion aller-retour Douala–Yaoundé — {far.number}",
            amount=1_150_000,
            date=timezone.localtime(far.event_start).date(),
            category=transport,
            reservation=far,
            supplier="Transports Kouassi & Fils",
            method="transfer",
            created_by=owner,
        )


def seed(owner: User) -> bool:
    if Invoice.objects.filter(reservation__status__in=SOLD).exists():
        return False
    _expenses(owner)
    today = timezone.localdate()
    for reservation in Reservation.objects.filter(status__in=SOLD).order_by("event_start"):
        confirmed = (reservation.confirmed_at or timezone.now()).date()
        if reservation.deposit_required:
            deposit = invoicing.issue(reservation, Invoice.Kind.DEPOSIT, user=owner)
            _backdate(deposit, confirmed, confirmed + timedelta(days=7))
        if reservation.status in FINAL_STATUSES:
            final = invoicing.issue(reservation, Invoice.Kind.FINAL, user=owner)
            event_day = timezone.localtime(reservation.event_start).date()
            _backdate(final, min(today, event_day - timedelta(days=10)), event_day - timedelta(7))
    # Exactly two invoices overdue at opening (§11): the others got a later due date.
    invoices = list(Invoice.objects.filter(reservation__status__in=SOLD))
    states = invoicing.states(invoices, today)
    overdue = sorted(
        (i for i in invoices if states[str(i.pk)].status == "overdue"),
        key=lambda i: (i.kind != Invoice.Kind.FINAL, i.due_at),
    )
    for invoice in overdue[2:]:
        _backdate(invoice, invoice.issued_at, today + timedelta(days=7))
    return True
