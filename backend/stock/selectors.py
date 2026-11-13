"""Reads of the stock screens (reservations-stock.md §5.5) and the dashboard (§8)."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from django.db.models import F, Sum

from . import availability
from .availability import Availability
from .models import Item, ItemUnit, Maintenance, Pack
from .services import today as local_today


def filter_by_state(items: list[Item], values: dict[str, Availability], state: str) -> list[Item]:
    def keep(item: Item) -> bool:
        value = values[str(item.pk)]
        if state == "available":
            return value.available > 0
        if state == "maintenance":
            return value.maintenance > 0
        if state == "out_of_service":
            return value.out_of_service > 0
        if state == "low":
            return item.alert_threshold > 0 and value.available <= item.alert_threshold
        return True

    return [item for item in items if keep(item)]


def pack_counts(packs: list[Pack], start: date, end: date) -> dict[str, int]:
    items = {c.item for pack in packs for c in pack.components.all()}
    values = availability.compute(items, start, end, local_today())
    return {str(pack.pk): availability.pack_available(pack, values) for pack in packs}


def grid(items: list[Item], start: date, days: int, today: date) -> dict[str, Any]:
    """Articles × days with the occupancy rate (used ÷ owned) of each cell."""
    daily = availability.daily_grid(items, start, days, today)
    rows = []
    for item in items:
        cells = []
        for value in daily[str(item.pk)]:
            used = value.total - value.available
            cells.append(
                {
                    "available": value.available,
                    "rate": round(used * 100 / value.total) if value.total else 0,
                }
            )
        rows.append(
            {
                "item": str(item.pk),
                "name": item.name,
                "reference": item.reference,
                "category": item.category.name,
                "total": item.total_quantity,
                "cells": cells,
            }
        )
    return {
        "days": [start + timedelta(days=offset) for offset in range(days)],
        "rows": rows,
    }


def stats() -> dict[str, Any]:
    from alerts.services import STOCK_KINDS, open_alerts

    active = Item.objects.filter(is_active=True)
    value = active.aggregate(total=Sum(F("total_quantity") * F("purchase_cost")))["total"]
    return {
        "items": active.count(),
        "units": active.aggregate(total=Sum("total_quantity"))["total"] or 0,
        "stock_value": int(value or 0),
        # Utilisation of the month joins with reservations (S4).
        "utilisation": None,
        "alerts": open_alerts().filter(kind__in=STOCK_KINDS).count(),
        "in_maintenance": Maintenance.objects.filter(ended_at__isnull=True).count(),
        "out_of_service": ItemUnit.objects.filter(status=ItemUnit.Status.OUT_OF_SERVICE).count(),
    }


def today_by_category() -> dict[str, Any]:
    """« Matériel aujourd'hui » (§8): per category, available / reserved / out / maintenance."""
    today = local_today()
    items = list(Item.objects.filter(is_active=True).select_related("category"))
    values = availability.compute(items, today, today, today)
    rows: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"available": 0, "reserved": 0, "out": 0, "maintenance": 0}
    )
    order: dict[str, int] = {}
    for item in items:
        value = values[str(item.pk)]
        row = rows[item.category.name]
        order[item.category.name] = item.category.position
        row["available"] += value.available
        row["reserved"] += value.reserved
        row["out"] += value.out
        row["maintenance"] += value.maintenance + value.out_of_service
    categories = [
        {"name": name, **rows[name]} for name in sorted(rows, key=lambda n: (order[n], n))
    ]
    return {
        "available": sum(c["available"] for c in categories),
        "categories": categories,
    }
