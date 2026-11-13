"""Management dashboard (reservations-stock.md §8): one call per period, cached 60 s.

Definitions, until reservations (S4) and invoices (S6) exist:
- revenue (« chiffre d'affaires réalisé »): contracts signed and reservations confirmed in the
  period;
- collected: payments received in the period (cancelled ones excluded);
- to collect: what remains due today on every live contract (a snapshot, not a period);
- estimated profit: revenue − direct costs of those contracts − general expenses (no wedding)
  dated in the period (costs follow the revenue they produced, not the day they are paid);
- average margin: (revenue − expenses of those contracts' weddings) ÷ revenue;
- average basket: revenue ÷ number of contracts;
- quote confirmation: accepted ÷ (accepted + refused + expired) decided in the period;
- collection rate: share of the installments due in the period that is paid.
Reservations count at their confirmation (revenue) and their payments (cash in); material
utilisation = rented piece-days ÷ owned piece-days. Staff check-in joins with step S7.
"""

from __future__ import annotations

import zoneinfo
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any

from django.core.cache import cache
from django.db.models import Count, DateField, QuerySet, Sum
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.utils import timezone

from accounts.models import Membership
from alerts import services as alert_services
from catalog.models import ServiceItem
from contracts.models import Contract, Payment
from contracts.services import allocate
from core.tenant import require_current_organization
from crm.models import Client
from documents.services import current_logo
from events import selectors as event_selectors
from events.models import Task, Wedding
from organizations.timezones import org_tz
from quotes.models import Quote, QuoteLine
from reservations import commitments
from reservations.models import Reservation, ReservationLine, ReservationPayment
from stock import selectors as stock_selectors

from . import selectors
from .models import Expense
from .periods import Period, last_months, resolve
from .visibility import can_see_balances, can_see_margins

CACHE_SECONDS = 60
PLANNING_DAYS = 7
TOP_SERVICES = 5
TOP_BALANCES = 5
CATEGORY_SLOTS = 5  # colored slots of the expense ring; the rest folds into « Autres »
MONTHS = [
    "janv.",
    "févr.",
    "mars",
    "avr.",
    "mai",
    "juin",
    "juil.",
    "août",
    "sept.",
    "oct.",
    "nov.",
    "déc.",
]


# --- Helpers ----------------------------------------------------------------------------------


def _pct(part: float, whole: float) -> float | None:
    return round(part * 100 / whole, 1) if whole else None


def _variation(current: float | None, previous: float | None) -> float | None:
    """% change; None when there is nothing to compare to."""
    if current is None or not previous:
        return None
    return round((current - previous) * 100 / abs(previous), 1)


def _delta(current: float | None, previous: float | None) -> float | None:
    """Difference in points (rates)."""
    if current is None or previous is None:
        return None
    return round(current - previous, 1)


def _contracts(tz: zoneinfo.ZoneInfo, start: date, end: date) -> QuerySet[Contract]:
    """Live contracts signed in the period."""
    contracts: QuerySet[Contract] = (
        Contract.objects.exclude(status=Contract.Status.CANCELLED)
        .annotate(day=TruncDate("signed_at", tzinfo=tz))
        .filter(day__range=(start, end))
    )
    return contracts


RES = Reservation.Status
SOLD = commitments.SOLD


def _reservations(tz: zoneinfo.ZoneInfo, start: date, end: date) -> QuerySet[Reservation]:
    """Reservations confirmed in the period (their revenue is earned at confirmation)."""
    rows: QuerySet[Reservation] = (
        Reservation.objects.filter(status__in=SOLD)
        .annotate(day=TruncDate("confirmed_at", tzinfo=tz))
        .filter(day__range=(start, end))
    )
    return rows


def _utilisation(tz: zoneinfo.ZoneInfo, start: date, end: date) -> float | None:
    """Rented piece-days ÷ owned piece-days over the period (equipment lines, packs expanded)."""
    from stock.models import Item

    days = (end - start).days + 1
    owned = sum(Item.objects.filter(is_active=True).values_list("total_quantity", flat=True))
    if not owned:
        return None
    used = 0
    today = timezone.now().astimezone(tz).date()
    lines = ReservationLine.objects.filter(
        reservation__status__in=SOLD,
        kind__in=(ReservationLine.Kind.RENTAL, ReservationLine.Kind.PACK),
    ).select_related("reservation", "pack")
    for line in lines:
        first, last = commitments.window(line.reservation, tz, today)
        overlap = (min(last, end) - max(first, start)).days + 1
        if overlap <= 0:
            continue
        pieces = (
            sum(c.quantity for c in line.pack.components.all()) * line.quantity
            if line.pack
            else line.quantity
        )
        used += pieces * overlap
    rate: float = round(min(100.0, used * 100 / (owned * days)), 1)
    return rate


def _expenses() -> QuerySet[Expense]:
    """Expenses with the day they count for (undated ones: the day they were entered)."""
    expenses: QuerySet[Expense] = Expense.objects.annotate(
        day=Coalesce("date", TruncDate("created_at"), output_field=DateField())
    )
    return expenses


def _sum(queryset: QuerySet[Any], field: str) -> int:
    return int(queryset.aggregate(total=Coalesce(Sum(field), 0))["total"])


# --- Period figures ---------------------------------------------------------------------------


def _window(tz: zoneinfo.ZoneInfo, start: date, end: date) -> dict[str, Any]:
    contracts = _contracts(tz, start, end)
    reservations = _reservations(tz, start, end)
    revenue = _sum(contracts, "total") + _sum(reservations, "total")
    count = contracts.count() + reservations.count()
    direct = _sum(Expense.objects.filter(wedding__contract__in=contracts.values("pk")), "amount")
    expenses = _sum(_expenses().filter(day__range=(start, end)), "amount")  # type: ignore[misc]
    general = _sum(
        _expenses().filter(wedding__isnull=True, day__range=(start, end)),  # type: ignore[misc]
        "amount",
    )
    collected = _sum(
        Payment.objects.filter(is_cancelled=False, paid_at__range=(start, end)), "amount"
    ) + _sum(
        ReservationPayment.objects.filter(
            kind=ReservationPayment.Kind.PAYMENT, is_cancelled=False, paid_at__range=(start, end)
        ),
        "amount",
    )

    quotes = Quote.objects.filter(is_template=False)
    accepted = (
        quotes.annotate(day=TruncDate("accepted_at", tzinfo=tz))
        .filter(day__range=(start, end))
        .count()
    )
    refused = (
        quotes.annotate(day=TruncDate("refused_at", tzinfo=tz))
        .filter(day__range=(start, end))
        .count()
    )
    expired = quotes.filter(status=Quote.Status.EXPIRED, valid_until__range=(start, end)).count()

    due = paid = 0
    live = Contract.objects.exclude(status=Contract.Status.CANCELLED).filter(
        schedule__due_date__range=(start, end)
    )
    for contract in live.distinct().prefetch_related("schedule"):
        for allocation in allocate(contract, contract.schedule.all()):
            if start <= allocation.schedule.due_date <= end:
                due += allocation.schedule.amount
                paid += allocation.paid

    return {
        "revenue": revenue,
        "contracts": count,
        "collected": collected,
        "expenses_dated": expenses,
        "profit": revenue - direct - general,
        "margin_avg": _pct(revenue - direct, revenue),
        "basket_avg": round(revenue / count) if count else None,
        "quote_confirmation": _pct(accepted, accepted + refused + expired),
        "collection_rate": _pct(paid, due),
        "utilisation": _utilisation(tz, start, end),
        "accepted": accepted,
        "refused": refused,
    }


def _to_collect() -> int:
    from reservations.selectors import with_money

    live = selectors.contracts_with_metrics().exclude(status=Contract.Status.CANCELLED)
    contracts = int(
        live.filter(balance__gt=0).aggregate(  # type: ignore[misc]
            total=Coalesce(Sum("balance"), 0)
        )["total"]
    )
    reservations = with_money().filter(status__in=SOLD, balance__gt=0)  # type: ignore[misc]
    return contracts + int(reservations.aggregate(total=Coalesce(Sum("balance"), 0))["total"])


def _monthly(tz: zoneinfo.ZoneInfo, today: date) -> list[dict[str, Any]]:
    """12 months: revenue (sparkline), income, expenses and profit (cash in − cash out)."""
    months = last_months(today, 12)
    first = months[0]
    revenue: dict[date, int] = defaultdict(int)
    income: dict[date, int] = defaultdict(int)

    def month_of(value: Any) -> date:
        return value.date() if isinstance(value, datetime) else value

    for rows_ in (
        Contract.objects.exclude(status=Contract.Status.CANCELLED)
        .annotate(month=TruncMonth("signed_at", tzinfo=tz))
        .filter(signed_at__date__gte=first)
        .values("month")
        .annotate(total=Sum("total")),
        Reservation.objects.filter(status__in=SOLD, confirmed_at__date__gte=first)
        .annotate(month=TruncMonth("confirmed_at", tzinfo=tz))
        .values("month")
        .annotate(total=Sum("total")),
    ):
        for row in rows_:
            revenue[month_of(row["month"])] += int(row["total"] or 0)
    for rows_ in (
        Payment.objects.filter(is_cancelled=False, paid_at__gte=first)
        .annotate(month=TruncMonth("paid_at"))
        .values("month")
        .annotate(total=Sum("amount")),
        ReservationPayment.objects.filter(
            kind=ReservationPayment.Kind.PAYMENT, is_cancelled=False, paid_at__gte=first
        )
        .annotate(month=TruncMonth("paid_at"))
        .values("month")
        .annotate(total=Sum("amount")),
    ):
        for row in rows_:
            income[month_of(row["month"])] += int(row["total"] or 0)
    spent = {
        row["month"]: row["total"]
        for row in _expenses()  # type: ignore[misc]
        .filter(day__gte=first)
        .annotate(month=TruncMonth("day"))
        .values("month")
        .annotate(total=Sum("amount"))
    }
    rows = []
    for month in months:
        cash_in = int(income.get(month, 0) or 0)
        cash_out = int(spent.get(month, 0) or 0)
        rows.append(
            {
                "month": month.isoformat()[:7],
                "label": MONTHS[month.month - 1],
                "revenue": int(revenue.get(month, 0) or 0),
                "income": cash_in,
                "expenses": cash_out,
                "profit": cash_in - cash_out,
            }
        )
    return rows


def _expenses_by_category(today: date, start: date, end: date) -> list[dict[str, Any]]:
    """Ring of the period. Colors follow the category, never its rank: the 5 largest
    categories of the last 12 months own slots 1–5, everything else is « Autres » (slot 0)."""
    year_start = last_months(today, 12)[0]
    slots = {
        row["category"]: index + 1
        for index, row in enumerate(
            _expenses()  # type: ignore[misc]
            .filter(day__gte=year_start, category__isnull=False)
            .values("category")
            .annotate(total=Sum("amount"))
            .order_by("-total", "category__position")[:CATEGORY_SLOTS]
        )
    }
    rows = (
        _expenses()  # type: ignore[misc]
        .filter(day__range=(start, end))
        .values("category", "category__name")
        .annotate(total=Sum("amount"))
    )
    result: list[dict[str, Any]] = []
    others = 0
    for row in rows:
        slot = slots.get(row["category"])
        if slot is None:
            others += int(row["total"])
        else:
            result.append(
                {
                    "id": str(row["category"]),
                    "name": row["category__name"],
                    "slot": slot,
                    "amount": int(row["total"]),
                }
            )
    result.sort(key=lambda r: r["slot"])
    if others:
        result.append({"id": None, "name": None, "slot": 0, "amount": others})
    return result


def _top_services(tz: zoneinfo.ZoneInfo, start: date, end: date) -> list[dict[str, Any]]:
    """Services of the quotes accepted in the period: how often, for how much."""
    lines = (
        QuoteLine.objects.filter(quote__is_template=False)
        .annotate(day=TruncDate("quote__accepted_at", tzinfo=tz))
        .filter(day__range=(start, end))
        .annotate(name=Coalesce("service_item__name", "label"))
        .values("name")
        .annotate(count=Count("quote", distinct=True), revenue=Sum("amount"))
        .order_by("-count", "-revenue", "name")[:TOP_SERVICES]
    )
    return [
        {"name": row["name"], "count": row["count"], "revenue": int(row["revenue"])}
        for row in lines
    ]


def _orders(tz: zoneinfo.ZoneInfo, start: date, end: date) -> dict[str, int]:
    """« Réservations » ring (§8): reservations whose event falls in the period."""
    rows = (
        Reservation.objects.annotate(day=TruncDate("event_start", tzinfo=tz))
        .filter(day__range=(start, end))
        .values_list("status", flat=True)
    )
    counts = {"confirmed": 0, "pending": 0, "cancelled": 0}
    for status in rows:
        if status == RES.CANCELLED:
            counts["cancelled"] += 1
        elif status in (RES.QUOTE_SENT, RES.AWAITING_DEPOSIT):
            counts["pending"] += 1
        elif status != RES.DRAFT:
            counts["confirmed"] += 1
    return counts


def _balances(today: date) -> list[dict[str, Any]]:
    contracts = list(
        selectors.contracts_with_metrics()  # type: ignore[misc]
        .exclude(status=Contract.Status.CANCELLED)
        .filter(balance__gt=0)
        .order_by("-balance")
        .prefetch_related("schedule")[:TOP_BALANCES]
    )
    from reservations.selectors import with_money

    rows: list[dict[str, Any]] = []
    for reservation in (
        with_money().filter(status__in=SOLD, balance__gt=0).order_by("-balance")[:TOP_BALANCES]  # type: ignore[misc]
    ):
        due = timezone.localtime(reservation.event_start).date()
        rows.append(
            {
                "contract": None,
                "reservation": str(reservation.pk),
                "number": reservation.number,
                "client_name": reservation.client.name,
                "balance": reservation.balance,  # type: ignore[attr-defined]
                "due_date": due,
                "is_overdue": due < today,
            }
        )
    for contract in contracts:
        next_due = next(
            (
                a.schedule.due_date
                for a in allocate(contract, contract.schedule.all())
                if a.remaining > 0
            ),
            None,
        )
        rows.append(
            {
                "contract": str(contract.pk),
                "reservation": None,
                "number": contract.number,
                "client_name": contract.client.name,
                "balance": contract.balance,  # type: ignore[attr-defined]
                "due_date": next_due,
                "is_overdue": bool(next_due and next_due < today),
            }
        )
    rows.sort(key=lambda row: -int(row["balance"]))
    return rows[:TOP_BALANCES]


# --- Today: planning, alerts, team ------------------------------------------------------------


# The 7 days come from the centralized calendar (§4.3), maintenance and teardowns aside.
PLANNING_KINDS = ("event", "delivery", "setup", "pickup", "return", "payment", "task")


def _planning(today: date) -> list[dict[str, Any]]:
    """The next 7 days: events, reservation logistics, tasks and payments expected."""
    from events import calendar

    end = today + timedelta(days=PLANNING_DAYS - 1)
    days: dict[date, list[dict[str, Any]]] = {
        today + timedelta(days=offset): [] for offset in range(PLANNING_DAYS)
    }
    for item in calendar.build(today, end, kinds=PLANNING_KINDS, movable=False, today=today):
        if item["status"] == RES.DRAFT:  # not promised to anyone yet
            continue
        # An event that started before today shows today (it is still running).
        days[max(item["date"], today)].append(item)
    return [{"date": day, "items": items} for day, items in days.items()]


def _team_today(today: date) -> list[dict[str, Any]]:
    """« Équipe du jour » (§8): the people on a mission today and their check-in (S7); before
    any staff assignment exists, the members with wedding tasks due today."""
    from staff.models import Assignment, Attendance

    tz = org_tz(require_current_organization())
    first = datetime.combine(today, time.min, tzinfo=tz)
    missions = (
        Assignment.objects.filter(start__lt=first + timedelta(days=1), end__gt=first)
        .exclude(reservation__status="cancelled")
        .select_related("staff", "attendance")
    )
    people: dict[str, dict[str, Any]] = {}
    for assignment in missions:
        entry = people.setdefault(
            assignment.staff.full_name,
            {"total": 0, "done": 0, "late": False, "absent": False, "in": 0},
        )
        entry["total"] += 1
        attendance = getattr(assignment, "attendance", None)
        if attendance is None:
            continue
        if attendance.status == Attendance.Status.ABSENT:
            entry["absent"] = True
        elif attendance.check_in:
            entry["in"] += 1
            entry["late"] |= attendance.status == Attendance.Status.LATE
            entry["done"] += attendance.check_out is not None
    if people:
        return [
            {
                "name": name,
                "total": entry["total"],
                "done": entry["done"],
                "status": (
                    "absent"
                    if entry["absent"]
                    else (
                        "done"
                        if entry["done"] == entry["total"]
                        else "in_progress" if entry["in"] else "todo"
                    )
                ),
                "late": entry["late"],
            }
            for name, entry in sorted(people.items())
        ]
    progress: dict[str, dict[str, Any]] = defaultdict(lambda: {"total": 0, "done": 0})
    for task in Task.objects.filter(due_date=today, assignee__isnull=False).select_related(
        "assignee"
    ):
        entry = progress[task.assignee.full_name]
        entry["total"] += 1
        entry["done"] += task.status == Task.Status.DONE
    return [
        {
            "name": name,
            "total": entry["total"],
            "done": entry["done"],
            "status": (
                "done"
                if entry["done"] == entry["total"]
                else "in_progress" if entry["done"] else "todo"
            ),
        }
        for name, entry in sorted(progress.items())
    ]


# --- Assembly ---------------------------------------------------------------------------------


def compute(period: Period, today: date) -> dict[str, Any]:
    tz = org_tz(require_current_organization())
    current = _window(tz, period.start, period.end)
    previous = _window(tz, period.previous_start, period.previous_end)
    planning = _planning(today)
    alert_services.refresh_if_stale()
    alerts = alert_services.sorted_open()
    weddings = list(
        event_selectors.weddings_with_metrics()
        .filter(status=Wedding.Status.PLANNED, date__gte=today)
        .order_by("date")[:5]
    )
    is_new = not (
        Contract.objects.exists()
        or Quote.objects.filter(is_template=False).exists()
        or Expense.objects.exists()
    )
    return {
        "period": {
            "key": period.key,
            "start": period.start,
            "end": period.end,
            "previous_start": period.previous_start,
            "previous_end": period.previous_end,
        },
        "is_new": is_new,
        "today": {
            "date": today,
            # Wedding records only: a reservation's event (seminar, birthday…) is not a wedding.
            "weddings_today": sum(
                1 for i in planning[0]["items"] if i["kind"] == "event" and i["wedding"]
            ),
            "weddings_week": sum(
                1 for d in planning for i in d["items"] if i["kind"] == "event" and i["wedding"]
            ),
            "events_today": sum(
                1 for i in planning[0]["items"] if i["kind"] == "event" and i["reservation"]
            ),
            "tasks_today": sum(1 for i in planning[0]["items"] if i["kind"] == "task"),
            "payments_today": sum(1 for i in planning[0]["items"] if i["kind"] == "payment"),
            "deliveries_today": sum(1 for i in planning[0]["items"] if i["kind"] == "delivery"),
            "returns_today": sum(
                1 for i in planning[0]["items"] if i["kind"] in ("pickup", "return")
            ),
        },
        "signature": {
            "revenue": current["revenue"],
            "revenue_variation": _variation(current["revenue"], previous["revenue"]),
            "collected": current["collected"],
            "to_collect": _to_collect(),
            "profit": current["profit"],
            "profit_variation": _variation(current["profit"], previous["profit"]),
        },
        "performance": {
            "utilisation": current["utilisation"],
            "utilisation_delta": _delta(current["utilisation"], previous["utilisation"]),
            "margin_avg": current["margin_avg"],
            "margin_avg_delta": _delta(current["margin_avg"], previous["margin_avg"]),
            "basket_avg": current["basket_avg"],
            "basket_avg_variation": _variation(current["basket_avg"], previous["basket_avg"]),
            "quote_confirmation": current["quote_confirmation"],
            "quote_confirmation_delta": _delta(
                current["quote_confirmation"], previous["quote_confirmation"]
            ),
            "collection_rate": current["collection_rate"],
            "collection_rate_delta": _delta(
                current["collection_rate"], previous["collection_rate"]
            ),
        },
        "orders": _orders(tz, period.start, period.end),
        "top_services": _top_services(tz, period.start, period.end),
        # « Matériel aujourd'hui » (§8): quantities only, shown to every role.
        "material_today": stock_selectors.today_by_category(),
        "upcoming_weddings": [
            {
                "id": str(w.pk),
                "title": w.title,
                "date": w.date,
                "days": (w.date - today).days if w.date else None,
                "venue": w.venue,
                "progress": event_selectors.progress(
                    w.tasks_done, w.tasks_total  # type: ignore[attr-defined]
                ),
                "tasks_total": w.tasks_total,  # type: ignore[attr-defined]
            }
            for w in weddings
        ],
        "monthly": _monthly(tz, today),
        "expenses_by_category": _expenses_by_category(today, period.start, period.end),
        "balances": _balances(today),
        "planning": planning,
        "alerts": alerts,
        "team_today": _team_today(today),
        "starter": {
            "catalog_items": ServiceItem.objects.filter(is_active=True).count(),
            "clients": Client.objects.filter(is_deleted=False, is_archived=False).count(),
            "has_logo": current_logo() is not None,
            "team_members": Membership.objects.filter(
                organization=require_current_organization(), is_active=True
            ).count(),
        },
    }


def strip_for_role(data: dict[str, Any], role: str | None) -> dict[str, Any]:
    """Amounts never leave the server for a role that must not see them (CLAUDE.md §11)."""
    data = dict(data)
    margins = can_see_margins(role)
    data["alerts"] = [a for a in data["alerts"] if alert_services.visible_to(a["kind"], role)]
    if not can_see_balances(role):
        data["signature"] = None
        data["performance"] = None
        data["monthly"] = None
        data["expenses_by_category"] = None
        data["balances"] = None
        data["top_services"] = [{**row, "revenue": None} for row in data["top_services"]]
        data["planning"] = [
            {**day, "items": [i for i in day["items"] if i["kind"] != "payment"]}
            for day in data["planning"]
        ]
        data["today"] = {**data["today"], "payments_today": None}
        return data
    if not margins:  # the planner: balances and cash in, no margins, profit or expenses
        data["signature"] = {
            **data["signature"],
            "profit": None,
            "profit_variation": None,
        }
        data["performance"] = {
            **data["performance"],
            "margin_avg": None,
            "margin_avg_delta": None,
        }
        data["monthly"] = [{**row, "expenses": None, "profit": None} for row in data["monthly"]]
        data["expenses_by_category"] = None
    return data


def _version_key(organization_id: Any) -> str:
    return f"org:{organization_id}:dashboard:version"


def invalidate(organization_id: Any) -> None:
    """Every cached period of the organization at once: the version changes."""
    key = _version_key(organization_id)
    if not cache.add(key, 1, None):
        try:
            cache.incr(key)
        except ValueError:  # expired between add and incr
            cache.set(key, 1, None)


def summary_for(
    role: str | None, key: str, start: date | None = None, end: date | None = None
) -> dict[str, Any]:
    organization = require_current_organization()
    today = timezone.now().astimezone(org_tz(organization)).date()
    period = resolve(key, today, start, end)
    version = cache.get(_version_key(organization.pk), 0)
    cache_key = (
        f"org:{organization.pk}:dashboard:{version}:{today}:{period.key}:"
        f"{period.start}:{period.end}"
    )
    data: dict[str, Any] | None = cache.get(cache_key)
    if data is None:
        data = compute(period, today)
        cache.set(cache_key, data, CACHE_SECONDS)
    return strip_for_role(data, role)


__all__ = ["compute", "invalidate", "summary_for"]
