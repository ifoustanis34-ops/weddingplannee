"""Profitability (docs/specs/reservations-stock.md §6.4).

- By event: revenue − direct costs = margin (amount and %). An event is a reservation (from its
  confirmation on, cancelled ones aside) or a wedding contract. Direct costs are the expenses
  attached to it (transport, consumables, subcontracting…) plus the staff at the pro rata of
  their hours (`staff.services.reservation_cost`). Breakage is always invoiced at the
  replacement price (« Casse et pertes »), so nothing of it stays unbilled.
- By service: revenue, number of sales and average margin — the margin of the events where the
  service was sold, weighted by what the service brought in (assumption: a service has no cost
  of its own in the catalogue).
- By stock item: cumulated rental revenue (pack lines shared by the components' rental
  prices), utilisation over the period, purchase cost and payback (« Rentabilisé à 78 % »).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any

from django.db.models import Sum
from django.utils import timezone

from core.tenant import require_current_organization
from organizations.timezones import org_tz

from .models import Expense
from .periods import Period


def pct(part: int, whole: int) -> float | None:
    return round(part * 100 / whole, 1) if whole else None


def _local_day(moment: datetime) -> date:
    return timezone.localtime(moment, org_tz(require_current_organization())).date()


# --- Events --------------------------------------------------------------------------------------


def by_event(period: Period) -> list[dict[str, Any]]:
    from contracts.models import Contract
    from reservations.commitments import SOLD
    from reservations.models import Reservation
    from staff.services import reservation_cost as staff_cost

    from .selectors import contracts_with_metrics

    tz = org_tz(require_current_organization())
    first = datetime.combine(period.start, time.min, tzinfo=tz)
    after = datetime.combine(period.end + timedelta(days=1), time.min, tzinfo=tz)
    costs = {
        row["reservation"]: row["total"]
        for row in Expense.objects.filter(reservation__isnull=False)
        .values("reservation")
        .annotate(total=Sum("amount"))
    }
    rows: list[dict[str, Any]] = []
    for reservation in Reservation.objects.filter(
        status__in=SOLD, event_start__gte=first, event_start__lt=after
    ).select_related("client"):
        expenses = int(costs.get(reservation.pk, 0))
        staff = staff_cost(reservation)
        spent = expenses + staff
        margin = reservation.total - spent
        rows.append(
            {
                "kind": "reservation",
                "id": str(reservation.pk),
                "number": reservation.number,
                "title": reservation.title,
                "client": reservation.client.name,
                "date": _local_day(reservation.event_start),
                "revenue": reservation.total,
                "costs": spent,
                "staff_costs": staff,
                "margin": margin,
                "margin_pct": pct(margin, reservation.total),
            }
        )
    for contract in (
        contracts_with_metrics()
        .exclude(status=Contract.Status.CANCELLED)
        .filter(wedding_date__range=(period.start, period.end))
    ):
        rows.append(
            {
                "kind": "contract",
                "id": str(contract.pk),
                "number": contract.number,
                "title": contract.wedding.title if contract.wedding else contract.client.name,
                "client": contract.client.name,
                "date": contract.wedding_date,
                "revenue": contract.total,
                "costs": contract.expenses,  # type: ignore[attr-defined]
                "staff_costs": 0,
                "margin": contract.margin,  # type: ignore[attr-defined]
                "margin_pct": pct(contract.margin, contract.total),  # type: ignore[attr-defined]
            }
        )
    rows.sort(key=lambda row: row["margin"], reverse=True)
    return rows


# --- Services ------------------------------------------------------------------------------------


def by_service(period: Period) -> list[dict[str, Any]]:
    from contracts.models import Contract
    from quotes.models import QuoteLine
    from reservations.models import ReservationLine

    events = {(row["kind"], row["id"]): row for row in by_event(period)}
    totals: dict[str, dict[str, Any]] = {}

    def add(key: str, name: str, amount: int, event: dict[str, Any] | None) -> None:
        row = totals.setdefault(
            key, {"key": key, "name": name, "revenue": 0, "sales": 0, "_weighted": 0.0, "_w": 0}
        )
        row["revenue"] += amount
        row["sales"] += 1
        if event and event["margin_pct"] is not None and amount > 0:
            row["_weighted"] += event["margin_pct"] * amount
            row["_w"] += amount

    reservation_ids = [key[1] for key in events if key[0] == "reservation"]
    for line in ReservationLine.objects.filter(
        reservation_id__in=reservation_ids, kind__in=("service", "free")
    ).select_related("service"):
        key = f"service:{line.service_id}" if line.service_id else f"label:{line.label.lower()}"
        name = line.service.name if line.service else line.label
        add(key, name, line.amount, events.get(("reservation", str(line.reservation_id))))
    quote_of = dict(
        Contract.objects.filter(
            pk__in=[key[1] for key in events if key[0] == "contract"]
        ).values_list("quote_id", "pk")
    )
    for line in QuoteLine.objects.filter(quote_id__in=list(quote_of)).select_related(
        "service_item"
    ):
        key = (
            f"service:{line.service_item_id}"
            if line.service_item_id
            else f"label:{line.label.lower()}"
        )
        name = line.service_item.name if line.service_item else line.label
        add(key, name, int(line.amount), events.get(("contract", str(quote_of[line.quote_id]))))
    rows = []
    for row in totals.values():
        weight = row.pop("_w")
        weighted = row.pop("_weighted")
        rows.append({**row, "margin_avg": round(weighted / weight, 1) if weight else None})
    rows.sort(key=lambda row: row["revenue"], reverse=True)
    return rows


# --- Stock items ---------------------------------------------------------------------------------


def by_item(period: Period) -> list[dict[str, Any]]:
    from reservations import commitments
    from reservations.commitments import SOLD
    from reservations.models import ReservationLine
    from stock.models import Item, PackComponent

    tz = org_tz(require_current_organization())
    today = timezone.now().astimezone(tz).date()
    items = {str(i.pk): i for i in Item.objects.filter(is_active=True).select_related("category")}
    components: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for component in PackComponent.objects.all():
        components[str(component.pack_id)].append((str(component.item_id), component.quantity))

    revenue: dict[str, int] = defaultdict(int)
    used: dict[str, int] = defaultdict(int)
    days = (period.end - period.start).days + 1
    for line in ReservationLine.objects.filter(
        reservation__status__in=SOLD, kind__in=("rental", "pack")
    ).select_related("reservation"):
        if line.kind == "rental" and line.item_id:
            shares = {str(line.item_id): line.amount}
            pieces = [(str(line.item_id), line.quantity)]
        else:
            parts = components.get(str(line.pack_id), [])
            weights = {
                item_id: qty * (items[item_id].rent_price if item_id in items else 0)
                for item_id, qty in parts
            }
            total_weight = sum(weights.values()) or 1
            shares = {k: line.amount * w // total_weight for k, w in weights.items()}
            pieces = [(item_id, qty * line.quantity) for item_id, qty in parts]
        for item_id, amount in shares.items():
            revenue[item_id] += amount
        first, last = commitments.window(line.reservation, tz, today)
        overlap = (min(last, period.end) - max(first, period.start)).days + 1
        if overlap > 0:
            for item_id, quantity in pieces:
                used[item_id] += quantity * overlap

    rows = []
    for item_id, item in items.items():
        cost = item.purchase_cost * item.total_quantity
        owned_days = item.total_quantity * days
        rows.append(
            {
                "id": item_id,
                "reference": item.reference,
                "name": item.name,
                "category": item.category.name,
                "revenue": revenue.get(item_id, 0),
                "rented_days": used.get(item_id, 0),
                "utilisation_pct": pct(used.get(item_id, 0), owned_days),
                "purchase_cost": cost,
                "payback_pct": pct(revenue.get(item_id, 0), cost),
            }
        )
    rows.sort(key=lambda row: row["revenue"], reverse=True)
    return rows


BUILDERS = {"event": by_event, "service": by_service, "item": by_item}
