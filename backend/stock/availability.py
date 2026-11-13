"""Availability of the equipment over a period (reservations-stock.md §5.2).

    available = owned − maintenance overlapping the period − units out of service
                − quantities reserved or out on overlapping periods (reservations, cleaning
                  delay included), taken on the busiest day of the period.

Pure reads; the reservation confirmation takes the row locks (``lock_items``) before checking.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from django.db.models import Q, QuerySet

from .models import Item, ItemUnit, Maintenance, Pack

FAR_FUTURE = date.max


@dataclass(frozen=True)
class Availability:
    item_id: str
    total: int
    maintenance: int
    out_of_service: int
    reserved: int
    out: int

    @property
    def available(self) -> int:
        return max(
            0, self.total - self.maintenance - self.out_of_service - self.reserved - self.out
        )


def maintenance_end(maintenance: Maintenance, today: date) -> date:
    """Last day the equipment is away: the eve of its return, else the expected end; an overdue
    maintenance blocks until it is closed (nobody knows when it comes back)."""
    if maintenance.ended_at is not None:
        return maintenance.ended_at - timedelta(days=1)  # back that day: available again
    if maintenance.expected_end is not None and maintenance.expected_end >= today:
        return maintenance.expected_end
    return FAR_FUTURE


@dataclass(frozen=True)
class _Span:
    first: date
    last: date
    quantity: int
    bucket: str  # "maintenance" | "reserved" | "out"


def _maintenance(
    item_ids: list[str], start: date, end: date, today: date
) -> dict[str, list[_Span]]:
    rows = Maintenance.objects.filter(item_id__in=item_ids, started_at__lte=end).filter(
        Q(ended_at__isnull=True) | Q(ended_at__gt=start)
    )
    per_item: dict[str, list[_Span]] = defaultdict(list)
    for m in rows:
        last = maintenance_end(m, today)
        if last >= start:
            per_item[str(m.item_id)].append(_Span(m.started_at, last, m.quantity, "maintenance"))
    return per_item


def _peak(spans: list[_Span], start: date, end: date) -> dict[str, int]:
    """Breakdown on the busiest day of the period (it can only change on a span's first day)."""
    best = {"maintenance": 0, "reserved": 0, "out": 0}
    candidates = {start} | {s.first for s in spans if start <= s.first <= end}
    for day in candidates:
        totals = {"maintenance": 0, "reserved": 0, "out": 0}
        for span in spans:
            if span.first <= day <= span.last:
                totals[span.bucket] += span.quantity
        if sum(totals.values()) > sum(best.values()):
            best = totals
    return best


def _out_of_service(item_ids: list[str]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for item_id in ItemUnit.objects.filter(
        item_id__in=item_ids, status=ItemUnit.Status.OUT_OF_SERVICE
    ).values_list("item_id", flat=True):
        counts[str(item_id)] += 1
    return counts


def compute(
    items: Iterable[Item],
    start: date,
    end: date,
    today: date,
    *,
    exclude_reservation: str | None = None,
) -> dict[str, Availability]:
    """``exclude_reservation``: leave one reservation out (checking or editing its own lines)."""
    from reservations import commitments

    items = list(items)
    ids = [str(i.pk) for i in items]
    spans = _maintenance(ids, start, end, today)
    delays = {str(i.pk): i.delay_days for i in items}
    for item_id, found in commitments.spans(
        ids, start, end, today, exclude=exclude_reservation, delays=delays
    ).items():
        spans[item_id].extend(_Span(s.first, s.last, s.quantity, s.bucket) for s in found)
    broken = _out_of_service(ids)
    result = {}
    for item in items:
        peak = _peak(spans.get(str(item.pk), []), start, end)
        result[str(item.pk)] = Availability(
            item_id=str(item.pk),
            total=item.total_quantity,
            maintenance=peak["maintenance"],
            out_of_service=broken.get(str(item.pk), 0),
            reserved=peak["reserved"],
            out=peak["out"],
        )
    return result


def pack_available(pack: Pack, availability: dict[str, Availability]) -> int:
    """A pack is available as many times as its scarcest component allows."""
    counts = [
        availability[str(c.item_id)].available // c.quantity
        for c in pack.components.all()
        if str(c.item_id) in availability
    ]
    return min(counts) if counts else 0


def daily_grid(
    items: list[Item], start: date, days: int, today: date
) -> dict[str, list[Availability]]:
    """Availability day by day (the 30-day « Disponibilité » view)."""
    grid: dict[str, list[Availability]] = {str(i.pk): [] for i in items}
    for offset in range(days):
        day = start + timedelta(days=offset)
        for item_id, value in compute(items, day, day, today).items():
            grid[item_id].append(value)
    return grid


def lock_items(item_ids: Iterable[str]) -> QuerySet[Item]:
    """Row locks, always in the same order, before checking and committing quantities."""
    return Item.objects.select_for_update().filter(pk__in=list(item_ids)).order_by("pk")
