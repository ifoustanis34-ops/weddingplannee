"""Quote arithmetic. FCFA amounts are integers; rounding is half-up to the franc.

The frontend mirrors these rules for the live preview; the server result is authoritative.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

HUNDRED = Decimal("100")


def _round(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def line_amount(unit_price: int, quantity: Decimal) -> int:
    return _round(Decimal(unit_price) * quantity)


@dataclass(frozen=True)
class Totals:
    subtotal: int
    discount_amount: int
    total: int
    deposit_amount: int
    balance: int


def compute_totals(
    line_amounts: Iterable[int], discount_pct: Decimal, deposit_pct: Decimal
) -> Totals:
    subtotal = sum(line_amounts)
    discount = _round(Decimal(subtotal) * discount_pct / HUNDRED)
    total = subtotal - discount
    deposit = _round(Decimal(total) * deposit_pct / HUNDRED)
    return Totals(subtotal, discount, total, deposit, total - deposit)
