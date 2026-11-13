"""What the reservations take from the stock over time (reservations-stock.md §5.2).

    reserved: committed reservations (awaiting deposit → in preparation), from the day the
              equipment leaves to the day it is back, plus each item's cleaning delay;
    out:      equipment checked out and not yet returned (a late return stays out until today).

A sale line holds its quantity until checkout; the sale movement then removes it from the stock.
"""

from __future__ import annotations

import zoneinfo
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from django.utils import timezone

from core.tenant import require_current_organization
from organizations.timezones import org_tz

from .models import Reservation, ReservationLine

Status = Reservation.Status
RESERVED = (Status.AWAITING_DEPOSIT, Status.CONFIRMED, Status.PREPARING)
OUT = (Status.DELIVERED, Status.INSTALLED, Status.IN_PROGRESS, Status.PICKED_UP)
# Reservations that count as orders (§4.4, §8): from the confirmation on.
SOLD = (*RESERVED, *OUT, Status.CLOSED)
FAR_FUTURE = date.max - timedelta(days=400)


@dataclass(frozen=True)
class Span:
    first: date
    last: date
    quantity: int
    bucket: str  # "reserved" | "out"
    reservation_id: str


def _day(moment: datetime | None, tz: zoneinfo.ZoneInfo) -> date | None:
    return timezone.localtime(moment, tz).date() if moment else None


def window(reservation: Reservation, tz: zoneinfo.ZoneInfo, today: date) -> tuple[date, date]:
    """From the day the equipment leaves to the day it is back at the warehouse."""
    first = (
        _day(reservation.delivery_at, tz)
        or _day(reservation.setup_at, tz)
        or _day(reservation.event_start, tz)
    )
    last = (
        _day(reservation.return_at, tz)
        or _day(reservation.pickup_at, tz)
        or _day(reservation.event_end, tz)
    )
    assert first is not None and last is not None
    if reservation.status in OUT and last < today:
        last = today  # late: still out until it comes back
    return first, max(first, last)


def spans(
    item_ids: list[str],
    start: date,
    end: date,
    today: date,
    *,
    exclude: str | None = None,
    delays: dict[str, int] | None = None,
) -> dict[str, list[Span]]:
    """Commitments of the given items overlapping [start, end], per item."""
    tz = org_tz(require_current_organization())
    delays = delays or {}
    lines = (
        ReservationLine.objects.filter(
            reservation__status__in=RESERVED + OUT,
            kind__in=[
                ReservationLine.Kind.RENTAL,
                ReservationLine.Kind.SALE,
                ReservationLine.Kind.PACK,
            ],
        )
        .select_related("reservation")
        .prefetch_related("pack__components")
    )
    if exclude:
        lines = lines.exclude(reservation_id=exclude)
    wanted = set(item_ids)
    result: dict[str, list[Span]] = defaultdict(list)
    for line in lines:
        reservation = line.reservation
        out = reservation.status in OUT
        first, last = window(reservation, tz, today)
        taken = line.quantity_out if out else line.quantity
        if taken <= 0:
            continue
        if line.kind == ReservationLine.Kind.PACK and line.pack is not None:
            parts = [(str(c.item_id), c.quantity * taken) for c in line.pack.components.all()]
        elif line.item_id is not None:
            if line.kind == ReservationLine.Kind.SALE and out:
                continue  # sold: the sale movement already removed it
            parts = [(str(line.item_id), taken)]
        else:
            continue
        for item_id, quantity in parts:
            if item_id not in wanted:
                continue
            span_last = (
                FAR_FUTURE
                if line.kind == ReservationLine.Kind.SALE
                else last + timedelta(days=delays.get(item_id, 0))
            )
            if span_last < start or first > end:
                continue
            result[item_id].append(
                Span(first, span_last, quantity, "out" if out else "reserved", str(reservation.pk))
            )
    return result
