"""Revenues recorded automatically (docs/specs/reservations-stock.md §6.1).

Every payment received creates its revenues, split by category in proportion to what the
client ordered (rental, sale, service, transport, damage): a 300 000 payment on a reservation
made of 80 % rental and 20 % transport gives 240 000 of rental and 60 000 of transport. The
split is exact (largest remainders), so revenues always add up to the payment. Cancelling a
payment cancels its revenues; nothing is ever deleted.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import Revenue, RevenueCategory

if TYPE_CHECKING:
    from contracts.models import Payment
    from reservations.models import Reservation, ReservationPayment

CATEGORY_OF_LINE = {
    "rental": RevenueCategory.RENTAL,
    "pack": RevenueCategory.RENTAL,
    "sale": RevenueCategory.SALE,
    "service": RevenueCategory.SERVICE,
    "free": RevenueCategory.SERVICE,
    "damage": RevenueCategory.DAMAGE,
}


def weights(reservation: Reservation) -> dict[str, int]:
    """What the client ordered, by revenue category (fees included, discount spread)."""
    totals: dict[str, int] = {}
    for line in reservation.lines.all():
        category = CATEGORY_OF_LINE.get(line.kind, RevenueCategory.SERVICE)
        totals[category] = totals.get(category, 0) + max(0, line.amount)
    if reservation.transport_fee:
        totals[RevenueCategory.TRANSPORT] = (
            totals.get(RevenueCategory.TRANSPORT, 0) + reservation.transport_fee
        )
    if reservation.setup_fee:
        totals[RevenueCategory.SERVICE] = (
            totals.get(RevenueCategory.SERVICE, 0) + reservation.setup_fee
        )
    return {k: v for k, v in totals.items() if v > 0} or {RevenueCategory.SERVICE: 1}


def split(amount: int, shares: dict[str, int]) -> dict[str, int]:
    """``amount`` shared in proportion to ``shares``, in whole francs, summing exactly."""
    total = sum(shares.values())
    exact = {key: amount * value / total for key, value in shares.items()}
    parts = {key: int(value) for key, value in exact.items()}
    left = amount - sum(parts.values())
    for key in sorted(exact, key=lambda k: exact[k] - parts[k], reverse=True)[:left]:
        parts[key] += 1
    return {key: value for key, value in parts.items() if value > 0}


def record_reservation_payment(payment: ReservationPayment) -> list[Revenue]:
    """Revenues of a reservation payment (the security deposit and its refund are not)."""
    from reservations.models import ReservationPayment

    if payment.kind != ReservationPayment.Kind.PAYMENT or payment.is_cancelled:
        return []
    reservation = payment.reservation
    return [
        Revenue.objects.create(
            amount=part,
            date=payment.paid_at,
            category=category,
            label=f"{reservation.number} · {reservation.title}",
            method=payment.method,
            client=reservation.client,
            reservation=reservation,
            reservation_payment=payment,
            created_by=payment.recorded_by,
        )
        for category, part in split(payment.amount, weights(reservation)).items()
    ]


def record_contract_payment(payment: Payment) -> list[Revenue]:
    """A wedding contract sells services: one revenue, « Prestation »."""
    if payment.is_cancelled:
        return []
    contract = payment.contract
    return [
        Revenue.objects.create(
            amount=payment.amount,
            date=payment.paid_at,
            category=RevenueCategory.SERVICE,
            label=f"{contract.number} · {contract.client.name}",
            method=payment.method,
            client=contract.client,
            contract=contract,
            contract_payment=payment,
            created_by=payment.recorded_by,
        )
    ]


def cancel_for_reservation_payment(payment: ReservationPayment) -> int:
    return Revenue.objects.filter(reservation_payment=payment).update(is_cancelled=True)


def cancel_for_contract_payment(payment: Payment) -> int:
    return Revenue.objects.filter(contract_payment=payment).update(is_cancelled=True)


def backfill() -> int:
    """Revenues of the payments recorded before revenues existed (idempotent)."""
    from contracts.models import Payment
    from reservations.models import ReservationPayment

    created = 0
    for reservation_payment in ReservationPayment.objects.filter(
        kind=ReservationPayment.Kind.PAYMENT, revenues__isnull=True
    ).select_related("reservation__client"):
        created += len(record_reservation_payment(reservation_payment))
    for contract_payment in Payment.objects.filter(revenues__isnull=True).select_related(
        "contract__client"
    ):
        created += len(record_contract_payment(contract_payment))
    for payment in ReservationPayment.objects.filter(is_cancelled=True):
        cancel_for_reservation_payment(payment)
    for cancelled in Payment.objects.filter(is_cancelled=True):
        cancel_for_contract_payment(cancelled)
    return created
