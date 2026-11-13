"""Reservations (reservations-stock.md §4.1, §5.2, §12, §13)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import datetime, time, timedelta
from typing import Any

import pytest
from django.db import connection
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Membership, User
from alerts import services as alert_services
from alerts.models import Alert
from core.exceptions import BusinessError
from core.tenant import tenant_context
from crm.models import Client
from finance.defaults import ensure_expense_categories
from organizations.models import Organization
from reservations import services
from reservations.models import Reservation, ReservationLine, ReservationPayment
from stock import availability
from stock import services as stock_services
from stock.defaults import ensure_item_categories
from stock.models import Item, ItemCategory, StockMovement

pytestmark = pytest.mark.django_db
Status = Reservation.Status
LIST = reverse("reservation-list")


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


def item(org: Organization, user: User, name: str, quantity: int, **extra: Any) -> Item:
    with tenant_context(org):
        created = stock_services.create_item(
            {
                "name": name,
                "category": ItemCategory.objects.get(name=extra.pop("category", "Mobilier")),
                "rent_price": extra.pop("rent", 2000),
                "purchase_cost": 14000,
                "deposit": 500,
                "initial_quantity": quantity,
                **extra,
            },
            user=user,
        )
        created.refresh_from_db()
    return created


def client_of(org: Organization, name: str = "Famille Ekotto") -> Client:
    with tenant_context(org):
        client: Client = Client.objects.create(name=name, email="ekotto@mail.cm")
    return client


def reserve(
    org: Organization,
    user: User,
    lines: list[services.LineInput],
    *,
    start: int = 10,
    days: int = 1,
    **extra: Any,
) -> Reservation:
    with tenant_context(org):
        reservation = services.create_reservation(
            {
                "client": extra.pop("client", None) or client_of(org, f"Client {start}"),
                "title": "Dot de la famille Ekotto",
                "event_start": at(start, 15),
                "event_end": at(start + days - 1, 23),
                "delivery_at": at(start - 1, 9),
                "return_at": at(start + days, 12),
                **extra,
            },
            lines,
            user=user,
        )
    return reservation


def rental(target: Item, quantity: int, **extra: Any) -> services.LineInput:
    return services.LineInput(kind="rental", item=target, quantity=quantity, **extra)


def free_now(org: Organization, target: Item, first: int, last: int) -> int:
    today = timezone.localdate()
    with tenant_context(org):
        fresh = Item.objects.select_related("category").get(pk=target.pk)
        return availability.compute(
            [fresh], today + timedelta(first), today + timedelta(last), today
        )[str(fresh.pk)].available


# --- Amounts ------------------------------------------------------------------------------------


def test_lines_fees_discount_deposit_and_caution(org_a: Organization, owner_a: User) -> None:
    chairs = item(org_a, owner_a, "Chaise Chiavari", 250)
    sono = item(org_a, owner_a, "Sono", 3, category="Sonorisation", rent=75000, rent_unit="day")
    reservation = reserve(
        org_a,
        owner_a,
        [
            rental(chairs, 100),  # 100 × 2 000
            rental(sono, 1, period_days=2),  # 75 000 × 2 days
            services.LineInput(kind="free", label="Montage spécial", unit_price=50_000),
        ],
        discount=20_000,
        transport_fee=35_000,
        setup_fee=15_000,
        deposit_pct=30,
    )
    assert reservation.subtotal == 200_000 + 150_000 + 50_000
    assert reservation.total == 400_000 - 20_000 + 35_000 + 15_000
    assert reservation.deposit_required == round(430_000 * 0.3)
    assert reservation.security_deposit == 100 * 500 + 500
    assert reservation.number.startswith(f"RES-{timezone.localdate().year}-")


def test_dates_follow_the_logistic_order(org_a: Organization, owner_a: User) -> None:
    chairs = item(org_a, owner_a, "Chaise", 10)
    with pytest.raises(BusinessError) as refused:
        reserve(org_a, owner_a, [rental(chairs, 1)], delivery_at=at(20))
    # Delivery after the event start: refused on the first date out of order.
    assert "event_start" in refused.value.fields


# --- Availability and confirmation (§5.2) --------------------------------------------------------


def test_confirmation_blocks_the_period_and_refuses_double_booking(
    org_a: Organization, owner_a: User
) -> None:
    chiavari = item(org_a, owner_a, "Chaise Chiavari", 250)
    first = reserve(org_a, owner_a, [rental(chiavari, 200)], start=10)
    with tenant_context(org_a):
        services.confirm(first, user=owner_a)
    assert free_now(org_a, chiavari, 9, 11) == 50

    clash = reserve(org_a, owner_a, [rental(chiavari, 80)], start=10)
    with tenant_context(org_a), pytest.raises(BusinessError) as refused:
        services.confirm(clash, user=owner_a)
    assert refused.value.error_code == "stock_insufficient"
    assert "80 demandés, 50 disponibles" in str(refused.value.detail)

    later = reserve(org_a, owner_a, [rental(chiavari, 250)], start=20)
    with tenant_context(org_a):
        services.confirm(later, user=owner_a)  # other dates: the whole stock again


def test_cleaning_delay_and_maintenance_count(org_a: Organization, owner_a: User) -> None:
    linen = item(org_a, owner_a, "Nappe ronde", 60, category="Linge de table")  # 1 day
    reservation = reserve(org_a, owner_a, [rental(linen, 60)], start=10)  # back on day 11
    with tenant_context(org_a):
        services.confirm(reservation, user=owner_a)
    assert free_now(org_a, linen, 12, 12) == 0  # at the pressing
    assert free_now(org_a, linen, 13, 13) == 60

    with tenant_context(org_a):
        stock_services.start_maintenance(linen, reason="Taches", quantity=5, user=owner_a)
        other = reserve(org_a, owner_a, [rental(linen, 60)], start=20)
        with pytest.raises(BusinessError):
            services.confirm(other, user=owner_a)


def test_packs_take_their_components(org_a: Organization, owner_a: User) -> None:
    chairs = item(org_a, owner_a, "Chaise Napoléon", 120)
    tables = item(org_a, owner_a, "Table ronde", 12)
    with tenant_context(org_a):
        pack = stock_services.save_pack(
            None,
            {
                "name": "Pack réception 100",
                "price": 290_000,
                "components": [{"item": chairs, "quantity": 100}, {"item": tables, "quantity": 10}],
            },
            user=owner_a,
        )
    reservation = reserve(org_a, owner_a, [services.LineInput(kind="pack", pack=pack, quantity=1)])
    assert reservation.total == 290_000
    with tenant_context(org_a):
        services.confirm(reservation, user=owner_a)
    assert free_now(org_a, chairs, 10, 10) == 20
    assert free_now(org_a, tables, 10, 10) == 2


@pytest.mark.django_db(transaction=True)
def test_two_simultaneous_confirmations_never_exceed_the_stock(
    org_a: Organization, owner_a: User
) -> None:
    """The last 10 chairs: two reservations of 6 confirmed at the same instant — one wins."""
    with tenant_context(org_a):
        ensure_item_categories()
    chairs = item(org_a, owner_a, "Chaise", 10)
    pending = [reserve(org_a, owner_a, [rental(chairs, 6)], start=10) for _ in range(2)]
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def worker(reservation: Reservation) -> None:
        try:
            with tenant_context(org_a):
                barrier.wait()
                services.confirm(reservation, user=owner_a)
                outcomes.append("confirmed")
        except BusinessError as error:
            outcomes.append(error.error_code)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(r,)) for r in pending]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["confirmed", "stock_insufficient"]
    assert free_now(org_a, chairs, 10, 10) == 4


# --- Deposit, checkout, return, cancellation ----------------------------------------------------


def test_deposit_turns_the_reservation_confirmed(org_a: Organization, owner_a: User) -> None:
    chairs = item(org_a, owner_a, "Chaise", 100)
    reservation = reserve(org_a, owner_a, [rental(chairs, 50)], deposit_required=30_000)
    with tenant_context(org_a):
        services.confirm(reservation, user=owner_a)
        reservation.refresh_from_db()
        assert reservation.status == Status.AWAITING_DEPOSIT
        with pytest.raises(BusinessError):
            services.checkout(reservation, None, user=owner_a)  # no deposit, no checkout
        with pytest.raises(BusinessError) as too_much:
            services.record_payment(
                reservation,
                amount=200_000,
                method="cash",
                paid_at=timezone.localdate(),
                user=owner_a,
            )
        assert too_much.value.error_code == "payment_exceeds_balance"
        services.record_payment(
            reservation, amount=30_000, method="wave", paid_at=timezone.localdate(), user=owner_a
        )
        reservation.refresh_from_db()
    assert reservation.status == Status.CONFIRMED
    assert free_now(org_a, chairs, 10, 10) == 50  # held since « en attente d’acompte »


def test_the_client_sheet_counts_reservations(
    client_for: Callable[..., APIClient], org_a: Organization, owner_a: User
) -> None:
    """§4.4: confirmed reservations are orders; drafts are not, and the caution is no revenue."""
    chairs = item(org_a, owner_a, "Chaise", 100)
    ekotto = client_of(org_a)
    sold = reserve(org_a, owner_a, [rental(chairs, 50)], client=ekotto, security_deposit=40_000)
    reserve(org_a, owner_a, [rental(chairs, 10)], client=ekotto, start=20)  # draft
    with tenant_context(org_a):
        services.confirm(sold, user=owner_a)
        services.record_payment(
            sold, amount=30_000, method="wave", paid_at=timezone.localdate(), user=owner_a
        )
        services.record_payment(
            sold,
            amount=40_000,
            method="cash",
            paid_at=timezone.localdate(),
            user=owner_a,
            kind="security",
        )
        sold.refresh_from_db()
        total = sold.total

    owner_client = client_for(owner_a, org_a)
    body = owner_client.get(reverse("client-detail", args=[ekotto.pk])).json()
    assert body["order_count"] == 1
    assert body["revenue"] == total
    assert body["collected"] == 30_000
    assert body["balance_due"] == total - 30_000
    assert body["last_order_at"] is not None

    history = owner_client.get(reverse("client-history", args=[ekotto.pk])).json()
    assert len(history["reservations"]) == 2
    assert sorted(p["kind"] for p in history["payments"]) == ["payment", "security"]
    assert {p["reference"] for p in history["payments"]} == {sold.number}


def test_checkout_and_return_bill_the_breakage(org_a: Organization, owner_a: User) -> None:
    glasses = item(org_a, owner_a, "Verre à pied", 500, category="Vaisselle", sale_price=1500)
    covers = item(org_a, owner_a, "Housse lycra", 500, category="Linge de table", sale_price=1500)
    reservation = reserve(org_a, owner_a, [rental(glasses, 200), rental(covers, 100)])
    with tenant_context(org_a):
        services.confirm(reservation, user=owner_a)
        services.checkout(reservation, None, user=owner_a)
        reservation.refresh_from_db()
        assert reservation.status == Status.DELIVERED
        assert StockMovement.objects.filter(kind="checkout").count() == 2
        lines = {line.item_id: line for line in reservation.lines.all()}
        services.advance(reservation, Status.PICKED_UP, user=owner_a)
        services.process_return(
            reservation,
            {
                str(lines[glasses.pk].pk): services.ReturnInput(returned=194, damaged=6),
                str(lines[covers.pk].pk): services.ReturnInput(returned=98, missing=2),
            },
            user=owner_a,
        )
        reservation.refresh_from_db()
        damage = list(reservation.lines.filter(kind=ReservationLine.Kind.DAMAGE))
        glasses.refresh_from_db()
        covers.refresh_from_db()

    assert reservation.status == Status.CLOSED
    assert {(d.quantity, d.unit_price) for d in damage} == {(6, 1500), (2, 1500)}
    assert reservation.total == 200 * 2000 + 100 * 2000 + 8 * 1500
    assert glasses.total_quantity == 494 and covers.total_quantity == 498
    assert free_now(org_a, glasses, 30, 30) == 494  # back in stock (pressing included)


def test_a_sale_leaves_the_stock_at_checkout(org_a: Organization, owner_a: User) -> None:
    linen = item(org_a, owner_a, "Nappe", 60, category="Linge de table", sale_price=6000)
    reservation = reserve(
        org_a, owner_a, [services.LineInput(kind="sale", item=linen, quantity=20)], kind="sale"
    )
    assert reservation.total == 120_000
    with tenant_context(org_a):
        services.confirm(reservation, user=owner_a)
        assert free_now(org_a, linen, 60, 60) == 40  # sold: held for good
        services.checkout(reservation, None, user=owner_a)
        linen.refresh_from_db()
    assert linen.total_quantity == 40


@pytest.mark.parametrize(("kept", "refund"), [(True, 20_000), (False, 50_000)])
def test_cancellation_releases_and_applies_the_policy(
    org_a: Organization, owner_a: User, kept: bool, refund: int
) -> None:
    Organization.objects.filter(pk=org_a.pk).update(deposit_kept_on_cancel=kept)
    org_a.refresh_from_db()
    chairs = item(org_a, owner_a, "Chaise", 100)
    reservation = reserve(org_a, owner_a, [rental(chairs, 100)], deposit_required=30_000)
    with tenant_context(org_a):
        services.confirm(reservation, user=owner_a)
        services.record_payment(
            reservation, amount=50_000, method="cash", paid_at=timezone.localdate(), user=owner_a
        )
        with pytest.raises(BusinessError):
            services.cancel(reservation, reason=" ", user=owner_a, request=None)
        services.cancel(reservation, reason="Mariage reporté", user=owner_a, request=None)
        reservation.refresh_from_db()
    assert reservation.status == Status.CANCELLED
    assert reservation.refund_due == refund
    assert free_now(org_a, chairs, 10, 10) == 100


def test_security_deposit_held_then_partly_retained(org_a: Organization, owner_a: User) -> None:
    chairs = item(org_a, owner_a, "Chaise", 100)
    reservation = reserve(org_a, owner_a, [rental(chairs, 10)])
    with tenant_context(org_a):
        services.confirm(reservation, user=owner_a)
        services.record_payment(
            reservation,
            amount=5_000,
            method="cash",
            paid_at=timezone.localdate(),
            user=owner_a,
            kind="security",
        )
        services.settle_security(
            reservation, retained=1_500, method="cash", user=owner_a, reason="Chaise rayée"
        )
        reservation.refresh_from_db()
        refund = ReservationPayment.objects.get(kind="security_refund")
        received = services.paid(reservation)
    assert reservation.security_status == Reservation.SecurityStatus.RETAINED
    assert refund.amount == 3_500
    assert received == 0  # the caution is not a payment


# --- API, roles, isolation, alerts --------------------------------------------------------------


def test_api_create_confirm_and_documents(
    client_for: Callable[..., APIClient], org_a: Organization, owner_a: User
) -> None:
    chairs = item(org_a, owner_a, "Chaise", 100)
    client = client_for(owner_a, org_a)
    created = client.post(
        LIST,
        {
            "client": str(client_of(org_a).pk),
            "title": "Baptême",
            "kind": "rental",
            "event_start": at(5).isoformat(),
            "event_end": at(5, 20).isoformat(),
            "lines": [{"kind": "rental", "item": str(chairs.pk), "quantity": 40}],
        },
        format="json",
    )
    assert created.status_code == 201, created.json()
    body = created.json()
    assert body["total"] == 80_000 and body["lines"][0]["label"] == "Chaise"
    confirmed = client.post(reverse("reservation-confirm", args=[body["id"]])).json()
    assert confirmed["status"] == "confirmed"
    pdf = client.get(reverse("reservation-document", args=[body["id"]]), {"type": "checkout"})
    assert pdf.content[:4] == b"%PDF"
    export = client.get(reverse("reservation-export"), {"type": "csv"})
    assert body["number"] in export.content.decode()


def test_roles(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
) -> None:
    chairs = item(org_a, owner_a, "Chaise", 100)
    reservation = reserve(org_a, owner_a, [rental(chairs, 10)])
    detail = reverse("reservation-detail", args=[reservation.pk])
    confirm = reverse("reservation-confirm", args=[reservation.pk])

    assistant = client_for(make_member(org_a, Membership.Role.ASSISTANT), org_a)
    seen = assistant.get(detail).json()
    assert seen["total"] is None and seen["lines"][0]["unit_price"] is None
    assert assistant.post(confirm).status_code == 403

    storekeeper = client_for(make_member(org_a, Membership.Role.STOREKEEPER), org_a)
    assert storekeeper.get(detail).json()["total"] is None
    assert storekeeper.post(confirm).status_code == 403
    client_for(owner_a, org_a).post(confirm)
    assert (
        storekeeper.post(reverse("reservation-checkout", args=[reservation.pk])).status_code == 200
    )
    pay = {"amount": 1000, "method": "cash", "paid_at": timezone.localdate().isoformat()}
    assert (
        storekeeper.post(reverse("reservation-payments", args=[reservation.pk]), pay).status_code
        == 403
    )
    accountant = client_for(make_member(org_a, Membership.Role.ACCOUNTANT), org_a)
    assert (
        accountant.post(reverse("reservation-payments", args=[reservation.pk]), pay).status_code
        == 201
    )
    team_lead = client_for(make_member(org_a, Membership.Role.TEAM_LEAD), org_a)
    assert team_lead.get(detail).status_code == 403


def test_organization_b_cannot_reach_reservations_of_a(
    client_for: Callable[..., APIClient],
    org_a: Organization,
    owner_a: User,
    org_b: Organization,
    owner_b: User,
) -> None:
    chairs = item(org_a, owner_a, "Chaise", 100)
    reservation = reserve(org_a, owner_a, [rental(chairs, 10)])
    other = client_for(owner_b, org_b)

    assert other.get(LIST).json() == []
    for name in ("reservation-detail", "reservation-shortages", "reservation-document"):
        assert other.get(reverse(name, args=[reservation.pk])).status_code == 404
    assert other.post(reverse("reservation-confirm", args=[reservation.pk])).status_code == 404
    stolen = other.post(
        LIST,
        {
            "client": str(reservation.client_id),
            "title": "Vol",
            "event_start": at(5).isoformat(),
            "event_end": at(5, 20).isoformat(),
            "lines": [{"kind": "rental", "item": str(chairs.pk), "quantity": 1}],
        },
        format="json",
    )
    assert stolen.status_code == 400


def test_shortage_and_late_return_alerts(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
) -> None:
    chiavari = item(org_a, owner_a, "Chaise Chiavari transparente", 250)
    draft = reserve(org_a, owner_a, [rental(chiavari, 280)], start=8)  # 280 for 250
    late = reserve(org_a, owner_a, [rental(chiavari, 10)], start=-5)
    with tenant_context(org_a):
        Reservation.objects.filter(pk=late.pk).update(status=Status.PICKED_UP)
        alert_services.refresh()
        alerts = {a.kind: a for a in alert_services.open_alerts()}
    assert alerts[Alert.Kind.STOCK_SHORTAGE].data["count"] == 280
    assert alerts[Alert.Kind.STOCK_SHORTAGE].data["reservation"] == str(draft.pk)
    assert alerts[Alert.Kind.LATE_RETURN].severity == Alert.Severity.CRITICAL

    shortages = (
        client_for(owner_a, org_a).get(reverse("reservation-shortages", args=[draft.pk])).json()
    )
    assert shortages[0]["needed"] == 280 and shortages[0]["available"] == 250


def test_reservation_tables_are_under_row_level_security() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM pg_class WHERE relname LIKE 'reservations\\_%%'"
            " AND relkind = 'r' AND relrowsecurity AND relforcerowsecurity"
        )
        assert cursor.fetchone() == (4,)
