from decimal import Decimal

import pytest

from quotes.calculations import compute_totals, line_amount


def test_reference_example_from_the_specification() -> None:
    """CLAUDE.md §7.5: contract 1 500 000, deposit 500 000 → balance 1 000 000."""
    totals = compute_totals([1_500_000], Decimal("0"), Decimal("33.3333"))

    assert totals.total == 1_500_000
    assert totals.deposit_amount == 500_000
    assert totals.balance == 1_000_000


def test_discount_then_deposit() -> None:
    totals = compute_totals([3_000_000, 1_200_000, 300_000], Decimal("10"), Decimal("30"))

    assert totals.subtotal == 4_500_000
    assert totals.discount_amount == 450_000
    assert totals.total == 4_050_000
    assert totals.deposit_amount == 1_215_000
    assert totals.balance == 2_835_000


@pytest.mark.parametrize(
    ("price", "quantity", "expected"),
    [
        (12_000, Decimal("250"), 3_000_000),
        (350_000, Decimal("1.5"), 525_000),
        (3, Decimal("0.5"), 2),
    ],
)
def test_line_amounts_round_half_up(price: int, quantity: Decimal, expected: int) -> None:
    assert line_amount(price, quantity) == expected
