"""Reads of the weddings module: progress, calendar (CLAUDE.md §7.6, complement §11)."""

from __future__ import annotations

from typing import Any

from django.db.models import Count, IntegerField, OuterRef, QuerySet, Subquery, Value
from django.db.models.functions import Coalesce

from .models import Task, Wedding


def _count(queryset: QuerySet[Any]) -> Coalesce:
    """Correlated COUNT: several counts on one wedding without multiplying the joins."""
    counted = queryset.order_by().values("wedding").annotate(n=Count("pk")).values("n")
    return Coalesce(Subquery(counted, output_field=IntegerField()), Value(0))


def weddings_with_metrics() -> QuerySet[Wedding]:
    from vendors.models import VendorAssignment

    tasks = Task.objects.filter(wedding=OuterRef("pk"))
    weddings: QuerySet[Wedding] = Wedding.objects.select_related("contract", "client").annotate(
        tasks_total=_count(tasks),
        tasks_done=_count(tasks.filter(status=Task.Status.DONE)),
        vendors_count=_count(VendorAssignment.objects.filter(wedding=OuterRef("pk"))),
    )
    return weddings


def progress(tasks_done: int, tasks_total: int) -> int:
    """Complement §16: tasks done ÷ total tasks, in percent."""
    return round(tasks_done * 100 / tasks_total) if tasks_total else 0


__all__ = ["progress", "weddings_with_metrics"]
