"""Payments and schedules (CLAUDE.md §7.5).

Payments settle the schedule in order. The balance of a contract is its total minus the
non-cancelled payments; a payment can never exceed it.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from accounts.models import User
from core import audit
from core.exceptions import BusinessError
from finance import revenues
from organizations.models import DocumentSequence
from organizations.numbering import next_number

from .models import Contract, Payment, PaymentSchedule

NNBSP = " "


def money(amount: int) -> str:
    return f"{amount:,}".replace(",", NNBSP) + " FCFA"


def plain(amount: int) -> str:
    return f"{amount:,}".replace(",", NNBSP)


def collected(contract: Contract) -> int:
    total = contract.payments.filter(is_cancelled=False).aggregate(total=Sum("amount"))["total"]
    return int(total or 0)


def balance(contract: Contract) -> int:
    return contract.total - collected(contract)


@dataclass(frozen=True)
class Allocation:
    schedule: PaymentSchedule
    paid: int

    @property
    def remaining(self) -> int:
        return self.schedule.amount - self.paid


def allocate(
    contract: Contract, schedules: Iterable[PaymentSchedule] | None = None
) -> list[Allocation]:
    """Spread what was collected over the schedule, in order (deposit first)."""
    available = collected(contract)
    allocations = []
    for schedule in (
        schedules if schedules is not None else contract.schedule.order_by("position", "due_date")
    ):
        paid = min(available, schedule.amount)
        available -= paid
        allocations.append(Allocation(schedule, paid))
    return allocations


def _sync(contract: Contract) -> None:
    """Recompute paid flags and the contract status."""
    for allocation in allocate(contract):
        is_paid = allocation.remaining == 0
        if allocation.schedule.is_paid != is_paid:
            allocation.schedule.is_paid = is_paid
            allocation.schedule.save(update_fields=["is_paid", "updated_at"])
    if contract.status != Contract.Status.CANCELLED:
        status = Contract.Status.COMPLETED if balance(contract) <= 0 else Contract.Status.ACTIVE
        if contract.status != status:
            contract.status = status
            contract.save(update_fields=["status", "updated_at"])


@transaction.atomic
def record_payment(
    contract: Contract,
    *,
    amount: int,
    method: str,
    paid_at: date,
    user: User,
    reference: str = "",
    proof: UploadedFile | None = None,
    request: Any = None,
) -> Payment:
    # Lock the contract: two payments recorded at once cannot both pass the balance check.
    contract = Contract.objects.select_for_update().get(pk=contract.pk)
    if contract.status == Contract.Status.CANCELLED:
        raise BusinessError(
            "contract_cancelled", "Ce contrat est annulé : aucun paiement possible."
        )
    remaining = balance(contract)
    if amount <= 0:
        raise BusinessError(
            "invalid", "Le montant doit être positif.", {"amount": ["Montant supérieur à 0."]}
        )
    if amount > remaining:
        raise BusinessError(
            "payment_exceeds_balance",
            f"Le montant dépasse le solde restant ({money(remaining)}).",
            {"amount": [f"Maximum {plain(remaining)}"]},
        )
    if paid_at > timezone.localdate():
        raise BusinessError(
            "invalid", "La date du paiement ne peut pas être future.", {"paid_at": ["Date future."]}
        )
    payment: Payment = Payment.objects.create(
        contract=contract,
        amount=amount,
        method=method,
        paid_at=paid_at,
        reference=reference.strip(),
        recorded_by=user,
        created_by=user,
        receipt_number=next_number(DocumentSequence.Kind.RECEIPT, year=paid_at.year),
    )
    if proof is not None:
        payment.proof.save(proof.name or "justificatif", proof, save=True)
    _sync(contract)
    revenues.record_contract_payment(payment)  # §6.1
    audit.record(
        "payment.recorded",
        payment,
        request=request,
        changes={"contract": contract.number, "amount": amount, "method": method},
    )
    from .tasks import send_receipt

    organization_id = str(contract.organization_id)
    transaction.on_commit(lambda: send_receipt.delay(organization_id, str(payment.pk)))
    return payment


@transaction.atomic
def cancel_payment(payment: Payment, *, reason: str, user: User, request: Any = None) -> Payment:
    if payment.is_cancelled:
        raise BusinessError("payment_cancelled", "Ce paiement est déjà annulé.")
    reason = reason.strip()
    if not reason:
        raise BusinessError(
            "invalid",
            "Indiquez pourquoi ce paiement est annulé.",
            {"reason": ["Motif obligatoire."]},
        )
    payment.is_cancelled = True
    payment.cancelled_at = timezone.now()
    payment.cancel_reason = reason
    payment.save(update_fields=["is_cancelled", "cancelled_at", "cancel_reason", "updated_at"])
    _sync(payment.contract)
    revenues.cancel_for_contract_payment(payment)
    audit.record(
        "payment.cancelled",
        payment,
        request=request,
        changes={"amount": payment.amount, "reason": reason, "contract": payment.contract.number},
    )
    return payment


@dataclass(frozen=True)
class ScheduleLine:
    label: str
    amount: int
    due_date: date


@transaction.atomic
def replace_schedule(
    contract: Contract, lines: list[ScheduleLine], *, user: User, request: Any = None
) -> None:
    """Edit installments. They must add up to the contract total and cover what is already paid."""
    if not lines:
        raise BusinessError("invalid", "Ajoutez au moins une échéance.")
    total = sum(line.amount for line in lines)
    if total != contract.total:
        raise BusinessError(
            "schedule_total_mismatch",
            f"Les échéances totalisent {money(total)} : "
            f"elles doivent faire {money(contract.total)}.",
        )
    if any(line.amount <= 0 for line in lines):
        raise BusinessError("invalid", "Chaque échéance doit avoir un montant positif.")
    old = list(contract.schedule.all())
    for schedule in old:
        schedule.delete()
    for position, line in enumerate(sorted(lines, key=lambda item: item.due_date)):
        PaymentSchedule.objects.create(
            contract=contract,
            label=line.label.strip() or f"Échéance {position + 1}",
            amount=line.amount,
            due_date=line.due_date,
            position=position,
            created_by=user,
        )
    _sync(contract)
    audit.record(
        "contract.schedule_updated",
        contract,
        request=request,
        changes={"installments": [[i.label, i.amount, i.due_date.isoformat()] for i in lines]},
    )
