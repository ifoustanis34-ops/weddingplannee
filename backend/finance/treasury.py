"""« Trésorerie » (docs/specs/reservations-stock.md §6.2): cash in, cash still to come, cash
out and the balance of the period, with the monthly curve of the last 12 months."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from django.db.models import Sum
from django.db.models.functions import Coalesce, TruncMonth

from .models import Expense, Invoice, Revenue, RevenueCategory
from .periods import Period, last_months


def _revenues(start: date, end: date) -> Any:
    return Revenue.objects.filter(is_cancelled=False, date__range=(start, end))


def _expenses(start: date, end: date) -> Any:
    return Expense.objects.filter(date__range=(start, end))


def _sum(queryset: Any, field: str = "amount") -> int:
    return int(queryset.aggregate(total=Coalesce(Sum(field), 0))["total"])


def compute(period: Period, today: date) -> dict[str, Any]:
    from . import dashboard, invoicing

    collected = _sum(_revenues(period.start, period.end))
    spent = _sum(_expenses(period.start, period.end))
    previous_collected = _sum(_revenues(period.previous_start, period.previous_end))
    previous_spent = _sum(_expenses(period.previous_start, period.previous_end))

    months = last_months(min(today, period.end), 12)
    cash_in: dict[date, int] = defaultdict(int)
    cash_out: dict[date, int] = defaultdict(int)
    for row in (
        _revenues(months[0], period.end)
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"))
    ):
        cash_in[row["month"]] += row["total"]
    for row in (
        _expenses(months[0], period.end)
        .annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(total=Sum("amount"))
    ):
        cash_out[row["month"]] += row["total"]

    by_category = {
        row["category"]: row["total"]
        for row in _revenues(period.start, period.end)
        .values("category")
        .annotate(total=Sum("amount"))
    }
    spent_by_category = [
        {"category": row["category__name"] or "Sans catégorie", "amount": row["total"]}
        for row in _expenses(period.start, period.end)
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    ]
    invoices = list(Invoice.objects.select_related("reservation"))
    states = invoicing.states(invoices, today)
    open_invoices = [s for s in states.values() if s.balance > 0]
    overdue = [s for s in states.values() if s.status == "overdue"]
    return {
        "period": {"start": period.start, "end": period.end, "key": period.key},
        "collected": collected,
        "to_collect": dashboard._to_collect(),
        "spent": spent,
        "balance": collected - spent,
        "previous": {
            "collected": previous_collected,
            "spent": previous_spent,
            "balance": previous_collected - previous_spent,
        },
        "invoices_open": sum(s.balance for s in open_invoices),
        "invoices_overdue": {"count": len(overdue), "amount": sum(s.balance for s in overdue)},
        "revenue_by_category": [
            {"category": value, "label": label, "amount": by_category.get(value, 0)}
            for value, label in RevenueCategory.choices
        ],
        "expenses_by_category": spent_by_category,
        "monthly": [
            {
                "month": month,
                "cash_in": cash_in.get(month, 0),
                "cash_out": cash_out.get(month, 0),
                "net": cash_in.get(month, 0) - cash_out.get(month, 0),
            }
            for month in months
        ],
    }
