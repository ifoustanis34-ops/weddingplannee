"""What deserves an alert today. Each condition yields the alert it would open (dedupe key)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta
from typing import Any

from django.db.models import Count, Min, Q
from django.utils import timezone

from contracts.models import Contract
from contracts.services import allocate
from core.tenant import require_current_organization
from events import selectors as event_selectors
from events.models import Task, Wedding
from organizations.timezones import org_tz

from .models import Alert

CRITICAL_AFTER_DAYS = 7
UNREADY_WINDOW_DAYS = 7


def unpaid_installments(start: date | None, end: date) -> list[dict[str, Any]]:
    """Unpaid parts of the installments due up to ``end`` (from ``start`` when given)."""
    filters = Q(schedule__due_date__lte=end)
    if start is not None:
        filters &= Q(schedule__due_date__gte=start)
    contracts = (
        Contract.objects.exclude(status=Contract.Status.CANCELLED)
        .filter(filters)
        .distinct()
        .select_related("client")
        .prefetch_related("schedule")
    )
    rows = []
    for contract in contracts:
        for allocation in allocate(contract, contract.schedule.all()):
            due = allocation.schedule.due_date
            if allocation.remaining > 0 and due <= end and (start is None or due >= start):
                rows.append(
                    {
                        "schedule": str(allocation.schedule.pk),
                        "contract": str(contract.pk),
                        "client_name": contract.client.name,
                        "label": allocation.schedule.label,
                        "due_date": due,
                        "remaining": allocation.remaining,
                    }
                )
    return rows


def current(today: date) -> Iterator[dict[str, Any]]:
    yield from stock(today)
    yield from reservations(today)
    yield from invoices(today)
    for row in unpaid_installments(None, today - timedelta(days=1)):
        late = (today - row["due_date"]).days
        yield {
            "dedupe_key": f"payment:{row['schedule']}",
            "kind": Alert.Kind.OVERDUE_PAYMENT,
            "severity": (
                Alert.Severity.CRITICAL if late > CRITICAL_AFTER_DAYS else Alert.Severity.SERIOUS
            ),
            "title": row["client_name"],
            "subtitle": row["label"],
            "occurred_on": row["due_date"],
            "data": {"amount": row["remaining"], "days": late, "contract": row["contract"]},
        }

    # Wedding tasks and readiness only with the « Mariages » module (feedback 13/11/2026).
    from core.tenant import require_current_organization

    if not require_current_organization().weddings_enabled:
        return

    late_tasks = (
        Task.objects.filter(due_date__lt=today)
        .exclude(status=Task.Status.DONE)
        .values("wedding", "wedding__title")
        .annotate(count=Count("pk"), oldest=Min("due_date"))
    )
    for row in late_tasks:
        yield {
            "dedupe_key": f"tasks:{row['wedding']}",
            "kind": Alert.Kind.LATE_TASKS,
            "severity": Alert.Severity.WARNING,
            "title": row["wedding__title"],
            "subtitle": "",
            "occurred_on": row["oldest"],
            "data": {"count": row["count"], "wedding": str(row["wedding"])},
        }

    soon = event_selectors.weddings_with_metrics().filter(
        status=Wedding.Status.PLANNED,
        date__range=(today, today + timedelta(days=UNREADY_WINDOW_DAYS)),
    )
    for wedding in soon:
        left = wedding.tasks_total - wedding.tasks_done  # type: ignore[attr-defined]
        if left <= 0 or wedding.date is None:
            continue
        yield {
            "dedupe_key": f"unready:{wedding.pk}:{wedding.date.isoformat()}",
            "kind": Alert.Kind.WEDDING_UNREADY,
            "severity": Alert.Severity.SERIOUS,
            "title": wedding.title,
            "subtitle": wedding.venue,
            "occurred_on": wedding.date,
            "data": {
                "count": left,
                "days": (wedding.date - today).days,
                "wedding": str(wedding.pk),
            },
        }


def invoices(today: date) -> Iterator[dict[str, Any]]:
    """Invoices past their due date with something left to pay (§6.3)."""
    from finance import invoicing
    from finance.models import Invoice

    issued = list(Invoice.objects.filter(due_at__lt=today).select_related("client", "reservation"))
    states = invoicing.states(issued, today)
    for invoice in issued:
        state = states[str(invoice.pk)]
        if state.status != "overdue":
            continue
        late = (today - invoice.due_at).days
        yield {
            "dedupe_key": f"invoice:{invoice.pk}",
            "kind": Alert.Kind.OVERDUE_INVOICE,
            "severity": (
                Alert.Severity.CRITICAL if late > CRITICAL_AFTER_DAYS else Alert.Severity.SERIOUS
            ),
            "title": invoice.client.name,
            "subtitle": invoice.number,
            "occurred_on": invoice.due_at,
            "data": {
                "amount": state.balance,
                "days": late,
                "invoice": str(invoice.pk),
                "reservation": str(invoice.reservation_id),
            },
        }


def stock(today: date) -> Iterator[dict[str, Any]]:
    """Stock alerts (reservations-stock.md §5.4)."""
    from stock import availability
    from stock.models import Item, ItemUnit, Maintenance

    items = list(Item.objects.filter(is_active=True, alert_threshold__gt=0))
    values = availability.compute(items, today, today, today)
    for item in items:
        left = values[str(item.pk)].available
        if left <= item.alert_threshold:
            yield {
                "dedupe_key": f"threshold:{item.pk}",
                "kind": Alert.Kind.BELOW_THRESHOLD,
                "severity": Alert.Severity.SERIOUS if left == 0 else Alert.Severity.WARNING,
                "title": item.name,
                "subtitle": item.reference,
                "occurred_on": today,
                "data": {"count": left, "threshold": item.alert_threshold, "item": str(item.pk)},
            }
    late = Maintenance.objects.filter(ended_at__isnull=True, expected_end__lt=today)
    for maintenance in late.select_related("item", "unit"):
        assert maintenance.expected_end is not None
        yield {
            "dedupe_key": f"maintenance:{maintenance.pk}",
            "kind": Alert.Kind.MAINTENANCE_LATE,
            "severity": Alert.Severity.SERIOUS,
            "title": maintenance.item.name,
            "subtitle": maintenance.unit.serial_number if maintenance.unit else maintenance.reason,
            "occurred_on": maintenance.expected_end,
            "data": {
                "days": (today - maintenance.expected_end).days,
                "item": str(maintenance.item_id),
            },
        }
    damaged = ItemUnit.objects.filter(
        condition=ItemUnit.Condition.DAMAGED, status=ItemUnit.Status.AVAILABLE
    ).select_related("item")
    for unit in damaged:
        yield {
            "dedupe_key": f"damaged:{unit.pk}",
            "kind": Alert.Kind.DAMAGED_UNIT,
            "severity": Alert.Severity.WARNING,
            "title": unit.item.name,
            "subtitle": unit.serial_number,
            "occurred_on": None,
            "data": {"item": str(unit.item_id)},
        }


def reservations(today: date) -> Iterator[dict[str, Any]]:
    """Coming reservations short of equipment, and equipment not back in time (§5.4)."""
    from reservations import commitments, services
    from reservations.models import Reservation

    tz = org_tz(require_current_organization())
    Status = Reservation.Status
    coming = Reservation.objects.filter(
        status__in=(
            Status.DRAFT,
            Status.QUOTE_SENT,
            Status.AWAITING_DEPOSIT,
            Status.CONFIRMED,
            Status.PREPARING,
        )
    ).select_related("client")
    for reservation in coming:
        first, _ = commitments.window(reservation, tz, today)
        if first < today:
            continue
        for shortage in services.shortages(reservation):
            committed = reservation.status in commitments.RESERVED
            yield {
                "dedupe_key": f"shortage:{reservation.pk}:{shortage.item.pk}",
                "kind": Alert.Kind.STOCK_SHORTAGE,
                "severity": Alert.Severity.CRITICAL if committed else Alert.Severity.SERIOUS,
                "title": shortage.item.name,
                "subtitle": f"{reservation.number} · {reservation.client.name}",
                "occurred_on": first,
                "data": {
                    "count": shortage.needed,
                    "available": shortage.available,
                    "reservation": str(reservation.pk),
                    "item": str(shortage.item.pk),
                },
            }
    out = Reservation.objects.filter(status__in=commitments.OUT).select_related("client")
    for reservation in out:
        due = reservation.return_at or reservation.pickup_at or reservation.event_end
        due_day = timezone.localtime(due, tz).date()
        if due_day >= today:
            continue
        late = (today - due_day).days
        yield {
            "dedupe_key": f"late_return:{reservation.pk}",
            "kind": Alert.Kind.LATE_RETURN,
            "severity": Alert.Severity.CRITICAL if late > 2 else Alert.Severity.SERIOUS,
            "title": reservation.client.name,
            "subtitle": f"{reservation.number} · {reservation.title}",
            "occurred_on": due_day,
            "data": {"days": late, "reservation": str(reservation.pk)},
        }
