"""Reads of the reservation screens (reservations-stock.md §4.2)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from django.db.models import (
    BigIntegerField,
    F,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from core.tenant import require_current_organization
from organizations.timezones import org_tz

from .models import Reservation, ReservationPayment

ZERO = Value(0, output_field=BigIntegerField())
Status = Reservation.Status
OPEN = (
    Status.QUOTE_SENT,
    Status.AWAITING_DEPOSIT,
    Status.CONFIRMED,
    Status.PREPARING,
    Status.DELIVERED,
    Status.INSTALLED,
    Status.IN_PROGRESS,
    Status.PICKED_UP,
    Status.CLOSED,
)
TAB_STATUSES: dict[str, tuple[str, ...]] = {
    "drafts": (Status.DRAFT, Status.QUOTE_SENT),
    "awaiting_deposit": (Status.AWAITING_DEPOSIT,),
    "confirmed": (Status.CONFIRMED, Status.PREPARING),
    "ongoing": (Status.DELIVERED, Status.INSTALLED, Status.IN_PROGRESS, Status.PICKED_UP),
    "closed": (Status.CLOSED,),
    "cancelled": (Status.CANCELLED,),
}


def with_money() -> QuerySet[Reservation]:
    """Paid (payments only, not the caution) and balance, by subquery: no double counting."""
    received = (
        ReservationPayment.objects.filter(
            reservation=OuterRef("pk"),
            kind=ReservationPayment.Kind.PAYMENT,
            is_cancelled=False,
        )
        .order_by()
        .values("reservation")
        .annotate(total=Sum("amount"))
        .values("total")
    )
    reservations: QuerySet[Reservation] = (
        Reservation.objects.select_related("client", "owner", "wedding")
        .annotate(paid=Coalesce(Subquery(received, output_field=BigIntegerField()), ZERO))
        .annotate(balance=F("total") - F("paid"))
    )
    return reservations


def _local_bounds(first: date, last: date) -> tuple[datetime, datetime]:
    tz = org_tz(require_current_organization())
    return (
        datetime.combine(first, time.min, tzinfo=tz),
        datetime.combine(last + timedelta(days=1), time.min, tzinfo=tz),
    )


def filter_list(queryset: QuerySet[Reservation], params: Any) -> QuerySet[Reservation]:
    tab = params.get("tab")
    if tab in TAB_STATUSES:
        queryset = queryset.filter(status__in=TAB_STATUSES[tab])
    if params.get("status"):
        queryset = queryset.filter(status__in=params["status"].split(","))
    if params.get("kind"):
        queryset = queryset.filter(kind=params["kind"])
    if params.get("owner"):
        queryset = queryset.filter(owner_id=params["owner"])
    if params.get("client"):
        queryset = queryset.filter(client_id=params["client"])
    if params.get("from") and params.get("to"):
        start, end = _local_bounds(
            date.fromisoformat(params["from"]), date.fromisoformat(params["to"])
        )
        queryset = queryset.filter(event_start__lt=end, event_end__gte=start)
    if params.get("search"):
        term = params["search"].strip()
        queryset = queryset.filter(
            Q(number__icontains=term)
            | Q(title__icontains=term)
            | Q(client__name__icontains=term)
            | Q(venue__icontains=term)
        )
    return queryset


def stats() -> dict[str, Any]:
    """Tiles (§4.2): confirmed this month, awaiting deposit, to deliver this week, to collect."""
    tz = org_tz(require_current_organization())
    today = timezone.now().astimezone(tz).date()
    month_start, month_end = _local_bounds(today.replace(day=1), today)
    week_start, week_end = _local_bounds(
        today - timedelta(days=today.weekday()), today + timedelta(days=6 - today.weekday())
    )
    rows = with_money()
    awaiting = rows.filter(status=Status.AWAITING_DEPOSIT)
    to_deliver = rows.filter(status__in=(Status.CONFIRMED, Status.PREPARING)).filter(
        Q(delivery_at__gte=week_start, delivery_at__lt=week_end)
        | Q(delivery_at__isnull=True, event_start__gte=week_start, event_start__lt=week_end)
    )
    open_rows = rows.exclude(status__in=(Status.DRAFT, Status.QUOTE_SENT, Status.CANCELLED))
    return {
        "confirmed_month": rows.filter(confirmed_at__gte=month_start, confirmed_at__lt=month_end)
        .exclude(status=Status.CANCELLED)
        .count(),
        "awaiting_deposit": awaiting.count(),
        "awaiting_deposit_amount": int(
            sum(max(0, r.deposit_required - r.paid) for r in awaiting)  # type: ignore[attr-defined]
        ),
        "to_deliver_week": to_deliver.count(),
        "balance_due": int(sum(max(0, r.balance) for r in open_rows)),  # type: ignore[attr-defined]
    }
