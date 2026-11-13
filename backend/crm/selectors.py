from __future__ import annotations

from typing import Any

from django.contrib.postgres.search import TrigramWordSimilarity
from django.db.models import (
    BigIntegerField,
    Count,
    DateTimeField,
    F,
    Max,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce, Greatest

from .models import Client, phone_key

ZERO = Value(0, output_field=BigIntegerField())


def active_clients() -> QuerySet[Client]:
    """Clients of the current organization (TenantManager), soft-deleted ones excluded."""
    return Client.objects.filter(is_deleted=False)


def with_metrics(queryset: QuerySet[Client]) -> QuerySet[Client]:
    """Orders, revenue, balance due and last order (subqueries: no double counting).

    Orders = live contracts + reservations from their confirmation on (reservations-stock.md
    §4.4); money received excludes the security deposit, which is not revenue.
    """
    from contracts.models import Contract, Payment
    from reservations.commitments import SOLD
    from reservations.models import Reservation, ReservationPayment

    live = Contract.objects.filter(client=OuterRef("pk")).exclude(status=Contract.Status.CANCELLED)
    revenue = live.order_by().values("client").annotate(total=Sum("total")).values("total")
    orders = live.order_by().values("client").annotate(n=Count("pk")).values("n")
    last = live.order_by().values("client").annotate(last=Max("signed_at")).values("last")
    paid = (
        Payment.objects.filter(contract__client=OuterRef("pk"), is_cancelled=False)
        .exclude(contract__status=Contract.Status.CANCELLED)
        .order_by()
        .values("contract__client")
        .annotate(total=Sum("amount"))
        .values("total")
    )
    sold = Reservation.objects.filter(client=OuterRef("pk"), status__in=SOLD).order_by()
    r_revenue = sold.values("client").annotate(total=Sum("total")).values("total")
    r_orders = sold.values("client").annotate(n=Count("pk")).values("n")
    r_last = sold.values("client").annotate(last=Max("confirmed_at")).values("last")
    r_paid = (
        ReservationPayment.objects.filter(
            reservation__client=OuterRef("pk"),
            reservation__status__in=SOLD,
            kind=ReservationPayment.Kind.PAYMENT,
            is_cancelled=False,
        )
        .order_by()
        .values("reservation__client")
        .annotate(total=Sum("amount"))
        .values("total")
    )

    def _sum(query: QuerySet[Any]) -> Coalesce:
        return Coalesce(Subquery(query, output_field=BigIntegerField()), ZERO)

    return (
        queryset.annotate(
            order_count=_sum(orders) + _sum(r_orders),
            revenue=_sum(revenue) + _sum(r_revenue),
            collected=_sum(paid) + _sum(r_paid),
            last_contract_at=Subquery(last, output_field=DateTimeField()),
            last_reservation_at=Subquery(r_last, output_field=DateTimeField()),
        )
        .annotate(
            last_order_at=Greatest(
                Coalesce("last_contract_at", "last_reservation_at"),
                Coalesce("last_reservation_at", "last_contract_at"),
            )
        )
        .annotate(balance_due=F("revenue") - F("collected"))
    )


def search(queryset: QuerySet[Client], term: str) -> QuerySet[Client]:
    """Typo-tolerant search on the name (pg_trgm), exact-ish on company, email and phone."""
    term = term.strip()
    if not term:
        return queryset
    condition = (
        Q(name__icontains=term) | Q(company__icontains=term) | Q(email__icontains=term.lower())
    )
    digits = phone_key(term)
    if len(digits) >= 4:
        condition |= Q(phone_key__contains=digits)
    return (
        queryset.annotate(similarity=TrigramWordSimilarity(term, "name"))
        .filter(condition | Q(similarity__gte=0.4))
        .order_by("-similarity", "name")
    )


def history(client: Client) -> dict[str, Any]:
    """Reservations, quotes, contracts and payments of a client, most recent first."""
    from contracts.models import Payment
    from reservations.models import ReservationPayment
    from reservations.selectors import with_money

    quotes = client.quotes.filter(is_template=False).order_by("-issue_date", "-created_at")
    contracts = client.contracts.order_by("-signed_at")
    payments = (
        Payment.objects.filter(contract__client=client)
        .select_related("contract")
        .order_by("-paid_at", "-created_at")
    )
    reservations = with_money().filter(client=client).order_by("-event_start")
    reservation_payments = (
        ReservationPayment.objects.filter(reservation__client=client)
        .select_related("reservation")
        .order_by("-paid_at", "-created_at")
    )
    rows = [
        {
            "id": p.id,
            "origin": "contract",
            "reference": p.contract.number,
            "kind": "payment",
            "amount": p.amount,
            "method": p.method,
            "paid_at": p.paid_at,
            "is_cancelled": p.is_cancelled,
            "created_at": p.created_at,
        }
        for p in payments
    ] + [
        {
            "id": p.id,
            "origin": "reservation",
            "reference": p.reservation.number,
            "kind": p.kind,
            "amount": p.amount,
            "method": p.method,
            "paid_at": p.paid_at,
            "is_cancelled": p.is_cancelled,
            "created_at": p.created_at,
        }
        for p in reservation_payments
    ]
    rows.sort(key=lambda row: (row["paid_at"], row["created_at"]), reverse=True)
    return {
        "reservations": reservations,
        "quotes": quotes,
        "contracts": contracts,
        "payments": rows,
    }
