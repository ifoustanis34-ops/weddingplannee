"""French formatting shared by the emails and the receipts. The quote PDF itself is rendered
by `documents.generation` (docs/specs/devis-billets.md §3)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .models import Quote

NNBSP = " "


def money(amount: int) -> str:
    """`1500000` → `1 500 000 FCFA` with narrow no-break spaces (CLAUDE.md §6)."""
    return f"{amount:,}".replace(",", NNBSP) + " FCFA"


def quantity(value: Decimal) -> str:
    text = f"{value.normalize():f}"
    return text.replace(".", ",")


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


def french_date(value: Any) -> str:
    if value is None:
        return "—"
    return f"{value.day} {MONTHS[value.month - 1]} {value.year}"


def percent(value: Decimal) -> str:
    return f"{value.normalize():f}".replace(".", ",") + " %"


def filename(quote: Quote) -> str:
    return f"{quote.number or 'modele'}.pdf"
