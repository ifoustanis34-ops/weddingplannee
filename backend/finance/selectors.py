"""Financial reads (CLAUDE.md §7.5). Amounts are integer FCFA."""

from __future__ import annotations

from datetime import date
from typing import Any, cast

from django.core.cache import cache
from django.db.models import (
    BigIntegerField,
    F,
    OuterRef,
    QuerySet,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from contracts.models import Contract, Payment
from contracts.services import allocate
from core.tenant import require_current_organization
from vendors import selectors as vendor_selectors

from .models import Expense

CACHE_SECONDS = 60
ZERO = Value(0, output_field=BigIntegerField())


def cache_key(name: str) -> str:
    return f"org:{require_current_organization().pk}:{name}"


def contracts_with_metrics() -> QuerySet[Contract]:
    """Contracts with collected, balance, expenses and margin (subqueries: no double counting)."""
    paid = (
        Payment.objects.filter(contract=OuterRef("pk"), is_cancelled=False)
        .order_by()
        .values("contract")
        .annotate(total=Sum("amount"))
        .values("total")
    )
    spent = (
        Expense.objects.filter(wedding__contract=OuterRef("pk"))
        .order_by()
        .values("wedding__contract")
        .annotate(total=Sum("amount"))
        .values("total")
    )
    contracts: QuerySet[Contract] = (
        Contract.objects.select_related("client", "wedding")
        .annotate(
            collected=Coalesce(Subquery(paid, output_field=BigIntegerField()), ZERO),
            expenses=Coalesce(Subquery(spent, output_field=BigIntegerField()), ZERO),
        )
        .annotate(balance=F("total") - F("collected"), margin=F("total") - F("expenses"))
    )
    return contracts


def margin_pct(total: int, margin: int) -> float | None:
    return round(margin * 100 / total, 1) if total else None


def overdue_amount(contracts: list[Contract], today: date) -> int:
    """Unpaid parts of installments whose due date has passed."""
    overdue = 0
    for contract in contracts:
        for allocation in allocate(contract):
            if allocation.schedule.due_date < today and allocation.remaining > 0:
                overdue += allocation.remaining
    return overdue


UPCOMING_LIMIT = 6


def upcoming_installments(contracts: list[Contract], today: date) -> list[dict[str, Any]]:
    """Next unpaid installments, overdue ones first (« Échéances à venir », complement §12)."""
    rows = []
    for contract in contracts:
        for allocation in allocate(contract):
            if allocation.remaining <= 0:
                continue
            schedule = allocation.schedule
            rows.append(
                {
                    "id": str(schedule.pk),
                    "contract": str(contract.pk),
                    "client_name": contract.client.name,
                    "label": schedule.label,
                    "due_date": schedule.due_date,
                    "remaining": allocation.remaining,
                    "is_overdue": schedule.due_date < today,
                }
            )
    rows.sort(key=lambda row: cast(date, row["due_date"]))
    return rows[:UPCOMING_LIMIT]


def compute_summary() -> dict[str, Any]:
    today = timezone.localdate()
    contracts = list(
        contracts_with_metrics()
        .exclude(status=Contract.Status.CANCELLED)
        .prefetch_related("schedule")
    )
    total = sum(c.total for c in contracts)
    collected = sum(c.collected for c in contracts)  # type: ignore[attr-defined]
    expenses = sum(c.expenses for c in contracts)  # type: ignore[attr-defined]
    month_start = today.replace(day=1)
    collected_this_month = int(
        Payment.objects.filter(
            is_cancelled=False,
            paid_at__gte=month_start,
            contract__status__in=["active", "completed"],
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )
    return {
        "contracts_count": len(contracts),
        "contracts_total": total,
        "collected": collected,
        "balance_due": total - collected,
        "collected_this_month": collected_this_month,
        "overdue": overdue_amount(contracts, today),
        "upcoming": upcoming_installments(contracts, today),
        "vendors_due": vendor_selectors.amounts_due(),
        "expenses": expenses,
        "margin": total - expenses,
        "margin_pct": margin_pct(total, total - expenses),
    }


def finance_summary() -> dict[str, Any]:
    """Cached 60 s in Redis; invalidated by `finance.signals` on every money movement."""
    key = cache_key("finance:summary")
    summary: dict[str, Any] | None = cache.get(key)
    if summary is None:
        summary = compute_summary()
        cache.set(key, summary, CACHE_SECONDS)
    return summary
