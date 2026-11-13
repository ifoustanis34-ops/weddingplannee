"""Centralized calendar (docs/specs/reservations-stock.md §4.3).

One feed for every screen that shows days — the calendar views, the logistic planning and the
dashboard's 7 days: reservation steps (delivery, setup, event, teardown, pickup, return),
weddings without a reservation, open tasks, equipment in maintenance and expected payments.
Colors are the front's business (§4.3: events ribbon, deliveries violet, setups fuchsia,
pickups coral, maintenance grey, payments gold).
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, time, timedelta
from typing import Any

from django.db.models import Q
from django.db.models.functions import Coalesce
from django.utils import timezone

from core.tenant import require_current_organization
from organizations.timezones import org_tz

from .models import Task, Wedding

KINDS = (
    "event",
    "delivery",
    "setup",
    "teardown",
    "pickup",
    "return",
    "maintenance",
    "payment",
    "task",
)
# Reservation steps shown as one-moment operations (the event itself spans its days).
STEPS = (
    ("delivery", "delivery_at"),
    ("setup", "setup_at"),
    ("teardown", "teardown_at"),
    ("pickup", "pickup_at"),
    ("return", "return_at"),
)
ORDER = {kind: index for index, kind in enumerate(KINDS)}
MAX_DAYS = 62


def _bounds(start: date, end: date) -> tuple[datetime, datetime]:
    tz = org_tz(require_current_organization())
    return (
        datetime.combine(start, time.min, tzinfo=tz),
        datetime.combine(end + timedelta(days=1), time.min, tzinfo=tz),
    )


def _item(kind: str, item_id: str, day: date, title: str, **extra: Any) -> dict[str, Any]:
    return {
        "kind": kind,
        "id": item_id,
        "date": day,
        "end_date": None,
        "time": None,
        "title": title,
        "subtitle": "",
        "status": None,
        "team": [],
        "owner": None,
        "vehicle": "",
        "wedding": None,
        "reservation": None,
        "contract": None,
        "item": None,
        "amount": None,
        "movable": False,
        **extra,
    }


def _reservations(
    start: date,
    end: date,
    *,
    member: str | None,
    statuses: Iterable[str] | None,
    with_money: bool,
    movable: bool,
) -> list[dict[str, Any]]:
    from reservations.commitments import SOLD
    from reservations.models import Reservation
    from reservations.selectors import with_money as reservations_with_money
    from reservations.services import EDITABLE

    tz = org_tz(require_current_organization())
    first, after = _bounds(start, end)
    rows = (
        reservations_with_money()
        .annotate(
            first_at=Coalesce("delivery_at", "setup_at", "event_start"),
            last_at=Coalesce("return_at", "pickup_at", "teardown_at", "event_end"),
        )
        .filter(first_at__lt=after, last_at__gte=first)
    )
    if statuses:
        rows = rows.filter(status__in=list(statuses))
    else:
        rows = rows.exclude(status=Reservation.Status.CANCELLED)
    if member:
        # Their reservations: as owner, or assigned to one of its steps (§7).
        rows = rows.filter(Q(owner__pk=member) | Q(assignments__staff__user__pk=member)).distinct()
    rows = rows.prefetch_related("assignments__staff")
    items: list[dict[str, Any]] = []
    for reservation in rows:
        crew: dict[str, list[str]] = {}
        for assignment in reservation.assignments.all():
            crew.setdefault(assignment.step, []).append(assignment.staff.full_name)

        def team(step: str, crew: dict[str, list[str]] = crew) -> list[str]:
            return sorted({*crew.get(step, []), *crew.get("all", [])})

        common = {
            "subtitle": f"{reservation.number} · {reservation.title}",
            "status": reservation.status,
            "owner": reservation.owner.full_name if reservation.owner else None,
            "vehicle": reservation.vehicle,
            "wedding": str(reservation.wedding_id) if reservation.wedding_id else None,
            "reservation": str(reservation.pk),
            "movable": movable and reservation.status in EDITABLE,
        }
        name = reservation.client.name
        begins = timezone.localtime(reservation.event_start, tz)
        ends = timezone.localtime(reservation.event_end, tz)
        if begins.date() <= end and ends.date() >= start:
            items.append(
                _item(
                    "event",
                    f"{reservation.pk}:event",
                    begins.date(),
                    name,
                    end_date=ends.date() if ends.date() != begins.date() else None,
                    time=begins.strftime("%H:%M"),
                    team=team("event"),
                    **common,
                )
            )
        for kind, field in STEPS:
            moment = getattr(reservation, field)
            if moment is None:
                continue
            local = timezone.localtime(moment, tz)
            if start <= local.date() <= end:
                items.append(
                    _item(
                        kind,
                        f"{reservation.pk}:{kind}",
                        local.date(),
                        name,
                        time=local.strftime("%H:%M"),
                        team=team(kind),
                        **common,
                    )
                )
        # The balance is expected by the event (same rule as the dashboard's balances).
        balance = reservation.balance  # type: ignore[attr-defined]
        if (
            with_money
            and not member
            and reservation.status in SOLD
            and reservation.status != Reservation.Status.CLOSED
            and balance > 0
            and start <= begins.date() <= end
        ):
            items.append(
                _item(
                    "payment",
                    f"{reservation.pk}:payment",
                    begins.date(),
                    name,
                    subtitle=f"Solde · {reservation.number}",
                    amount=balance,
                    reservation=str(reservation.pk),
                    status=reservation.status,
                )
            )
    return items


def _weddings(start: date, end: date) -> list[dict[str, Any]]:
    """Weddings without a live reservation (the reservation's event stands for them)."""
    rows = (
        Wedding.objects.filter(date__range=(start, end))
        .exclude(status=Wedding.Status.CANCELLED)
        .exclude(reservations__status__in=_live_reservation_statuses())
        .prefetch_related("tasks__assignee")
        .distinct()
    )
    items = []
    for wedding in rows:
        team = sorted({t.assignee.full_name for t in wedding.tasks.all() if t.assignee is not None})
        items.append(
            _item(
                "event",
                str(wedding.pk),
                wedding.date,
                wedding.title,
                subtitle=wedding.venue,
                team=team,
                wedding=str(wedding.pk),
            )
        )
    return items


def _live_reservation_statuses() -> list[str]:
    from reservations.models import Reservation

    return [s for s in Reservation.Status.values if s != Reservation.Status.CANCELLED]


def _tasks(start: date, end: date, member: str | None) -> list[dict[str, Any]]:
    rows = (
        Task.objects.filter(due_date__range=(start, end), status=Task.Status.TODO)
        .select_related("assignee", "wedding")
        .order_by("due_date", "title")
    )
    if member:
        rows = rows.filter(assignee_id=member)
    return [
        _item(
            "task",
            str(task.pk),
            task.due_date,
            task.title,
            subtitle=task.wedding.title,
            team=[task.assignee.full_name] if task.assignee else [],
            wedding=str(task.wedding_id),
        )
        for task in rows
    ]


def _maintenance(start: date, end: date, today: date) -> list[dict[str, Any]]:
    from stock.models import Maintenance

    rows = (
        Maintenance.objects.filter(started_at__lte=end)
        .filter(Q(ended_at__isnull=True) | Q(ended_at__gte=start))
        .select_related("item")
    )
    items = []
    for row in rows:
        # Open and overdue: blocked until closed, shown up to today at least (stock rule).
        last = row.ended_at or max(row.expected_end or today, today)
        first = max(row.started_at, start)
        if last < start:
            continue
        items.append(
            _item(
                "maintenance",
                str(row.pk),
                first,
                f"{row.item.name} × {row.quantity}",
                end_date=last if last != first else None,
                subtitle=row.reason,
                item=str(row.item_id),
            )
        )
    return items


def _installments(start: date, end: date) -> list[dict[str, Any]]:
    from alerts.conditions import unpaid_installments

    return [
        _item(
            "payment",
            f"{row['contract']}:{row['schedule']}",
            row["due_date"],
            row["client_name"],
            subtitle=row["label"],
            amount=row["remaining"],
            contract=row["contract"],
        )
        for row in unpaid_installments(start, end)
    ]


def build(
    start: date,
    end: date,
    *,
    member: str | None = None,
    kinds: Iterable[str] | None = None,
    statuses: Iterable[str] | None = None,
    with_money: bool = True,
    movable: bool = True,
    today: date | None = None,
) -> list[dict[str, Any]]:
    """Every item between ``start`` and ``end`` (inclusive), in the order of each day.

    ``member`` keeps that person's reservations (as owner) and tasks — maintenance and money
    belong to no one and leave; ``statuses`` filters the reservations; ``with_money`` hides
    payments from the roles that do not see balances (§12).
    """
    today = today or timezone.now().astimezone(org_tz(require_current_organization())).date()
    wanted = set(kinds) if kinds else set(KINDS)
    items = _reservations(
        start, end, member=member, statuses=statuses, with_money=with_money, movable=movable
    )
    # Weddings and their tasks only with the « Mariages » module (feedback 13/11/2026).
    weddings_on = require_current_organization().weddings_enabled
    if weddings_on and "event" in wanted and not statuses:
        items += _weddings(start, end)
    if weddings_on and "task" in wanted and not statuses:
        items += _tasks(start, end, member)
    if not member and not statuses:
        if "maintenance" in wanted:
            items += _maintenance(start, end, today)
        if with_money and "payment" in wanted:
            items += _installments(start, end)
    items = [i for i in items if i["kind"] in wanted]
    items.sort(key=lambda i: (i["date"], i["time"] or "99:99", ORDER[i["kind"]], i["title"]))
    return items


__all__ = ["KINDS", "MAX_DAYS", "build"]
