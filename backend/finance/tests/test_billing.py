"""Revenues, invoices, credit notes, treasury, receipts (reservations-stock.md §6.1–§6.3)."""

from __future__ import annotations

import io
from collections.abc import Callable
from datetime import datetime, time, timedelta
from typing import Any

import pytest
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import Membership, User
from alerts import services as alert_services
from alerts.models import Alert
from core.exceptions import BusinessError
from core.tenant import tenant_context
from crm.models import Client
from finance import invoicing, revenues
from finance.defaults import ensure_expense_categories
from finance.models import CreditNote, Expense, ExpenseCategory, Invoice, Revenue
from organizations.models import Organization
from reservations import services
from reservations.models import Reservation
from stock import services as stock_services
from stock.defaults import ensure_item_categories
from stock.models import ItemCategory


@pytest.fixture(autouse=True)
def _defaults(org_a: Organization, org_b: Organization) -> None:
    for organization in (org_a, org_b):
        with tenant_context(organization):
            ensure_item_categories()
            ensure_expense_categories()


def at(days: int, hour: int = 10) -> datetime:
    return timezone.make_aware(
        datetime.combine(timezone.localdate() + timedelta(days=days), time(hour))
    )


def booked(org: Organization, user: User, *, start: int = 20, **extra: Any) -> Reservation:
    """100 chairs at 800 (80 000 of rental) + 20 000 of transport = 100 000, confirmed."""
    with tenant_context(org):
        chairs = stock_services.create_item(
            {
                "name": f"Chaise {start}",
                "category": ItemCategory.objects.get(name="Mobilier"),
                "rent_price": 800,
                "initial_quantity": 200,
            },
            user=user,
        )
        reservation = services.create_reservation(
            {
                "client": Client.objects.create(name="Famille Mbarga"),
                "title": "Dot Mbarga",
                "delivery_at": at(start - 1, 9),
                "event_start": at(start, 15),
                "event_end": at(start, 23),
                "return_at": at(start + 1, 12),
                "transport_fee": 20_000,
                "deposit_required": 30_000,
                **extra,
            },
            [services.LineInput(kind="rental", item=chairs, quantity=100)],
            user=user,
        )
        services.confirm(reservation, user=user)
        reservation.refresh_from_db()
    return reservation


def pay(reservation: Reservation, user: User, amount: int, kind: str = "payment") -> Any:
    return services.record_payment(
        reservation,
        amount=amount,
        method="wave",
        paid_at=timezone.localdate(),
        user=user,
        kind=kind,
    )


def test_each_payment_becomes_revenues_split_by_category(
    org_a: Organization, owner_a: User
) -> None:
    reservation = booked(org_a, owner_a)
    assert reservation.total == 100_000
    with tenant_context(org_a):
        payment = pay(reservation, owner_a, 50_001)
        pay(reservation, owner_a, 15_000, kind="security")  # a caution is not revenue
        rows = {r.category: r.amount for r in Revenue.objects.filter(reservation=reservation)}
        assert rows == {"rental": 40_001, "transport": 10_000}  # exact, sums to the payment
        assert all(r.client_id == reservation.client_id for r in Revenue.objects.all())

        services.cancel_payment(payment, reason="Chèque rejeté", user=owner_a, request=None)
        assert not Revenue.objects.filter(is_cancelled=False).exists()
        assert Revenue.objects.count() == 2  # never deleted
        assert revenues.backfill() == 0  # idempotent


def test_split_is_exact_and_proportional() -> None:
    assert revenues.split(100, {"a": 1, "b": 1, "c": 1}) == {"a": 34, "b": 33, "c": 33}
    assert sum(revenues.split(999_999, {"a": 7, "b": 3}).values()) == 999_999


def test_deposit_then_final_invoice_numbers_and_statuses(
    org_a: Organization, owner_a: User
) -> None:
    reservation = booked(org_a, owner_a)
    year = timezone.localdate().year
    with tenant_context(org_a):
        deposit = invoicing.issue(reservation, Invoice.Kind.DEPOSIT, user=owner_a)
        assert (deposit.number, deposit.total) == (f"FA-{year}-0001", 30_000)
        final = invoicing.issue(reservation, Invoice.Kind.FINAL, user=owner_a)
        assert (final.number, final.total) == (f"FA-{year}-0002", 70_000)
        labels = [line.label for line in final.lines.all()]
        assert labels[-1] == f"Déjà facturé — {deposit.number}"
        assert sum(line.amount for line in final.lines.all()) == 70_000

        # Nothing left to invoice: refused, and the refusal uses no number.
        with pytest.raises(BusinessError):
            invoicing.issue(reservation, Invoice.Kind.FINAL, user=owner_a)

        pay(reservation, owner_a, 40_000)  # deposit paid, 10 000 on the final
        states = invoicing.states([deposit, final])
        assert states[str(deposit.pk)].status == "paid"
        assert (states[str(final.pk)].status, states[str(final.pk)].balance) == ("partial", 60_000)

        Invoice.objects.filter(pk=final.pk).update(due_at=timezone.localdate() - timedelta(10))
        assert invoicing.states([final])[str(final.pk)].status == "overdue"
        alert_services.refresh()
        alert = Alert.objects.get(kind=Alert.Kind.OVERDUE_INVOICE)
        assert (alert.subtitle, alert.data["amount"]) == (final.number, 60_000)


@pytest.mark.parametrize("kept_policy", [True, False])
def test_cancellation_issues_credit_notes_per_policy(
    org_a: Organization, owner_a: User, kept_policy: bool
) -> None:
    org_a.deposit_kept_on_cancel = kept_policy
    org_a.save()
    reservation = booked(org_a, owner_a)
    with tenant_context(org_a):
        deposit = invoicing.issue(reservation, Invoice.Kind.DEPOSIT, user=owner_a)
        final = invoicing.issue(reservation, Invoice.Kind.FINAL, user=owner_a)
        pay(reservation, owner_a, 30_000)
        services.cancel(reservation, reason="Mariage reporté", user=owner_a, request=None)
        credits = {note.invoice_id: note.amount for note in CreditNote.objects.all()}
        if kept_policy:  # the deposit stays invoiced and paid; the rest is cancelled
            assert credits == {final.pk: 70_000}
        else:
            assert credits == {deposit.pk: 30_000, final.pk: 70_000}
        assert all(n.number.startswith("AV-") for n in CreditNote.objects.all())
        assert invoicing.invoiced(reservation) == (30_000 if kept_policy else 0)


def test_a_credit_note_never_exceeds_the_invoice(org_a: Organization, owner_a: User) -> None:
    reservation = booked(org_a, owner_a)
    with tenant_context(org_a):
        invoice = invoicing.issue(reservation, Invoice.Kind.DEPOSIT, user=owner_a)
        invoicing.credit(invoice, amount=10_000, reason="Geste commercial", user=owner_a)
        with pytest.raises(BusinessError):
            invoicing.credit(invoice, amount=20_001, reason="Trop", user=owner_a)
        assert invoicing.states([invoice])[str(invoice.pk)].net == 20_000


def test_api_roles_pdf_and_isolation(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    org_b: Organization,
    owner_a: User,
    owner_b: User,
) -> None:
    reservation = booked(org_a, owner_a)
    owner = client_for(owner_a, org_a)
    created = owner.post(
        reverse("invoice-list"), {"reservation": str(reservation.pk), "kind": "deposit"}
    )
    assert created.status_code == 201, created.json()
    body = created.json()
    assert (body["status"], body["balance"], body["kind_label"]) == (
        "issued",
        30_000,
        "Facture d’acompte",
    )
    pdf = owner.get(reverse("invoice-pdf", args=[body["id"]]))
    assert pdf["Content-Type"] == "application/pdf" and pdf.content.startswith(b"%PDF")

    credit = owner.post(
        reverse("invoice-credit", args=[body["id"]]), {"amount": 5_000, "reason": "Geste"}
    )
    assert credit.status_code == 201
    note_pdf = owner.get(reverse("credit-note-pdf", args=[credit.json()["id"]]))
    assert note_pdf.content.startswith(b"%PDF")

    planner = client_for(make_member(org_a, Membership.Role.PLANNER), org_a)
    assert planner.get(reverse("invoice-list")).status_code == 200
    issue = {"reservation": str(reservation.pk), "kind": "final"}
    assert planner.post(reverse("invoice-list"), issue).status_code == 403
    assert planner.get(reverse("finance-treasury")).status_code == 403
    assistant = client_for(make_member(org_a, Membership.Role.ASSISTANT), org_a)
    assert assistant.get(reverse("invoice-list")).status_code == 403

    other = client_for(owner_b, org_b)
    assert other.get(reverse("invoice-detail", args=[body["id"]])).status_code == 404
    assert other.get(reverse("invoice-list")).json() == []
    assert other.post(reverse("invoice-list"), issue).status_code == 400


def test_treasury_of_the_period(
    client_for: Callable[..., APIClient], org_a: Organization, owner_a: User
) -> None:
    reservation = booked(org_a, owner_a)
    with tenant_context(org_a):
        pay(reservation, owner_a, 60_000)
        Expense.objects.create(
            label="Loyer entrepôt",
            amount=25_000,
            date=timezone.localdate(),
            category=ExpenseCategory.objects.get(name="Loyer de l’entrepôt"),
        )
    data = client_for(owner_a, org_a).get(reverse("finance-treasury"), {"period": "month"}).json()
    assert (data["collected"], data["spent"], data["balance"]) == (60_000, 25_000, 35_000)
    assert data["to_collect"] == 40_000
    rental = next(row for row in data["revenue_by_category"] if row["category"] == "rental")
    assert rental["amount"] == 48_000
    assert data["monthly"][-1]["net"] == 35_000
    assert len(data["monthly"]) == 12


def test_expense_receipt_is_private_and_checked(
    client_for: Callable[..., APIClient], org_a: Organization, owner_a: User
) -> None:
    reservation = booked(org_a, owner_a)
    owner = client_for(owner_a, org_a)
    created = owner.post(
        reverse("expense-list"),
        {"label": "Carburant Kribi", "amount": 45_000, "reservation": str(reservation.pk)},
        format="json",
    ).json()
    assert created["reservation_number"] == reservation.number
    assert created["category_name"] == "Sous-traitance"  # attached, no category given

    png = io.BytesIO()
    Image.new("RGB", (40, 30), "white").save(png, "PNG")
    png.seek(0)
    png.name = "ticket.png"
    url = reverse("expense-receipt", args=[created["id"]])
    uploaded = owner.post(url, {"file": png}, format="multipart")
    assert uploaded.status_code == 200
    assert "/api/v1/files/" in uploaded.json()["receipt_url"]
    with tenant_context(org_a):
        assert Expense.objects.get(pk=created["id"]).receipt.name.startswith(f"org/{org_a.pk}/")

    svg = io.BytesIO(b"<svg xmlns='http://www.w3.org/2000/svg'><script>x</script></svg>")
    svg.name = "x.svg"
    assert owner.post(url, {"file": svg}, format="multipart").status_code == 400


# --- Profitability and reports (§6.4, §6.5) ------------------------------------------------------


def test_profitability_by_event_item_and_service(
    client_for: Callable[..., APIClient], org_a: Organization, owner_a: User
) -> None:
    reservation = booked(org_a, owner_a, start=3)
    with tenant_context(org_a):
        Expense.objects.create(
            label="Carburant", amount=30_000, date=timezone.localdate(), reservation=reservation
        )
        Item = reservation.lines.first().item.__class__  # type: ignore[union-attr]
        Item.objects.filter(pk=reservation.lines.first().item_id).update(  # type: ignore[union-attr]
            purchase_cost=1_000
        )
    owner = client_for(owner_a, org_a)
    events = owner.get(reverse("finance-profitability"), {"by": "event", "period": "month"})
    row = next(r for r in events.json()["rows"] if r["number"] == reservation.number)
    assert (row["revenue"], row["costs"], row["margin"], row["margin_pct"]) == (
        100_000,
        30_000,
        70_000,
        70.0,
    )
    items = owner.get(reverse("finance-profitability"), {"by": "item", "period": "month"}).json()
    chair = items["rows"][0]
    # 80 000 of rental for 200 chairs bought 1 000 each: « Rentabilisé à 40 % ».
    assert (chair["revenue"], chair["purchase_cost"], chair["payback_pct"]) == (
        80_000,
        200_000,
        40.0,
    )
    assert chair["rented_days"] == 100 * 3  # delivery eve → return the day after
    assert owner.get(reverse("finance-profitability"), {"by": "x"}).status_code == 400


@pytest.mark.parametrize(
    "kind",
    ["revenue", "profitable", "services", "items", "clients", "expenses", "margins", "unpaid"],
)
def test_every_report_in_json(
    client_for: Callable[..., APIClient], org_a: Organization, owner_a: User, kind: str
) -> None:
    reservation = booked(org_a, owner_a, start=3)
    with tenant_context(org_a):
        pay(reservation, owner_a, 40_000)
    body = client_for(owner_a, org_a).get(reverse("report", args=[kind]), {"period": "month"})
    assert body.status_code == 200
    data = body.json()
    assert data["type"] == kind and data["columns"] and "headline" in data
    if kind == "revenue":
        assert data["totals"]["total"] == 40_000
    if kind == "unpaid":
        assert data["totals"]["balance"] == 60_000


def test_report_outputs_and_rights(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
) -> None:
    reservation = booked(org_a, owner_a, start=3)
    with tenant_context(org_a):
        pay(reservation, owner_a, 40_000)
    owner = client_for(owner_a, org_a)
    url = reverse("report", args=["margins"])
    pdf = owner.get(url, {"period": "month", "output": "pdf"})
    assert pdf["Content-Type"] == "application/pdf" and pdf.content.startswith(b"%PDF")
    xlsx = owner.get(url, {"period": "quarter", "output": "xlsx"})
    assert xlsx.content.startswith(b"PK")
    assert owner.get(reverse("report", args=["nope"])).status_code == 404
    accountant = client_for(make_member(org_a, Membership.Role.ACCOUNTANT), org_a)
    assert accountant.get(url).status_code == 200
    planner = client_for(make_member(org_a, Membership.Role.PLANNER), org_a)
    assert planner.get(url).status_code == 403
