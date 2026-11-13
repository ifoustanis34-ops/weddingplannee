"""Dashboard periods (reservations-stock.md §8): the current one and the one it is compared to."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from core.exceptions import BusinessError

PERIODS = ("today", "week", "month", "quarter", "year", "custom")
MAX_CUSTOM_DAYS = 3 * 366


@dataclass(frozen=True)
class Period:
    key: str
    start: date  # inclusive
    end: date  # inclusive
    previous_start: date
    previous_end: date

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1


def _month_start(day: date) -> date:
    return day.replace(day=1)


def _add_months(day: date, months: int) -> date:
    """First day of the month ``months`` after (or before) the month of ``day``."""
    index = day.year * 12 + day.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def resolve(key: str, today: date, start: date | None = None, end: date | None = None) -> Period:
    """Calendar periods compare to the previous calendar period; « custom » to the same length
    just before it."""
    if key not in PERIODS:
        raise BusinessError("invalid", "Période inconnue.", {"period": ["Période inconnue."]})
    if key == "today":
        return Period(key, today, today, today - timedelta(days=1), today - timedelta(days=1))
    if key == "week":
        monday = today - timedelta(days=today.weekday())
        return Period(
            key,
            monday,
            monday + timedelta(days=6),
            monday - timedelta(days=7),
            monday - timedelta(days=1),
        )
    if key == "month":
        first = _month_start(today)
        return Period(
            key,
            first,
            _add_months(first, 1) - timedelta(days=1),
            _add_months(first, -1),
            first - timedelta(days=1),
        )
    if key == "quarter":
        first = date(today.year, 3 * ((today.month - 1) // 3) + 1, 1)
        return Period(
            key,
            first,
            _add_months(first, 3) - timedelta(days=1),
            _add_months(first, -3),
            first - timedelta(days=1),
        )
    if key == "year":
        first = date(today.year, 1, 1)
        return Period(
            key,
            first,
            date(today.year, 12, 31),
            date(today.year - 1, 1, 1),
            date(today.year - 1, 12, 31),
        )
    if start is None or end is None:
        raise BusinessError(
            "invalid",
            "Choisissez les dates de début et de fin.",
            {"from": ["Date obligatoire."], "to": ["Date obligatoire."]},
        )
    if end < start:
        raise BusinessError(
            "invalid", "La fin doit suivre le début.", {"to": ["Date antérieure au début."]}
        )
    length = (end - start).days + 1
    if length > MAX_CUSTOM_DAYS:
        raise BusinessError("invalid", "Trois ans au maximum.", {"to": ["Période trop longue."]})
    return Period(
        key,
        start,
        end,
        start - timedelta(days=length),
        start - timedelta(days=1),
    )


def last_months(today: date, count: int) -> list[date]:
    """First day of the ``count`` last months, oldest first, current month included."""
    first = _month_start(today)
    return [_add_months(first, -offset) for offset in reversed(range(count))]


def from_params(params: Any, today: date) -> Period:
    """``?period=&from=&to=`` of the finance screens and reports (month by default)."""
    try:
        start = date.fromisoformat(params["from"]) if params.get("from") else None
        end = date.fromisoformat(params["to"]) if params.get("to") else None
    except ValueError as exc:
        raise BusinessError("invalid", "Date illisible (AAAA-MM-JJ).") from exc
    return resolve(params.get("period", "month"), today, start, end)
