"""Contracts and payment schedules. Created by converting an accepted quote (CLAUDE.md §7.3).

Payments, cancellations and financial screens arrive with step 7.
"""

from __future__ import annotations

from django.db import models

from core.models import TenantModel


class Contract(TenantModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "En cours"
        COMPLETED = "completed", "Soldé"
        CANCELLED = "cancelled", "Annulé"

    number = models.CharField(max_length=32)
    quote = models.OneToOneField("quotes.Quote", on_delete=models.PROTECT, related_name="contract")
    client = models.ForeignKey("crm.Client", on_delete=models.PROTECT, related_name="contracts")
    total = models.BigIntegerField()
    signed_at = models.DateTimeField()
    wedding_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

    class Meta(TenantModel.Meta):
        ordering = ["-signed_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "number"], name="unique_contract_number"
            ),
            models.CheckConstraint(
                condition=models.Q(total__gte=0), name="contract_total_positive"
            ),
        ]

    def __str__(self) -> str:
        return self.number


class PaymentSchedule(TenantModel):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="schedule")
    label = models.CharField(max_length=80)
    amount = models.BigIntegerField()
    due_date = models.DateField()
    is_paid = models.BooleanField(default=False)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta(TenantModel.Meta):
        ordering = ["position", "due_date"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=0), name="schedule_amount_positive"
            )
        ]

    def __str__(self) -> str:
        return f"{self.label} ({self.amount})"


class Payment(TenantModel):
    """Money received for a contract. Never deleted: a mistake is cancelled (CLAUDE.md §7.5)."""

    class Method(models.TextChoices):
        TRANSFER = "transfer", "Virement"
        CASH = "cash", "Espèces"
        ORANGE_MONEY = "orange_money", "Orange Money"
        MTN_MOMO = "mtn_momo", "MTN MoMo"
        WAVE = "wave", "Wave"
        CHEQUE = "cheque", "Chèque"

    contract = models.ForeignKey(Contract, on_delete=models.PROTECT, related_name="payments")
    amount = models.BigIntegerField()
    method = models.CharField(max_length=16, choices=Method.choices)
    paid_at = models.DateField()
    reference = models.CharField(max_length=120, blank=True)
    proof = models.FileField(upload_to="payments/proofs/", blank=True)
    receipt_number = models.CharField(max_length=32, blank=True)
    receipt_file = models.FileField(upload_to="payments/receipts/", blank=True)
    recorded_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    is_cancelled = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.TextField(blank=True)

    class Meta(TenantModel.Meta):
        ordering = ["-paid_at", "-created_at"]
        indexes = [
            models.Index(fields=["organization", "paid_at"]),
            models.Index(fields=["contract", "is_cancelled"]),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="payment_amount_positive")
        ]

    def __str__(self) -> str:
        return f"{self.amount} — {self.contract_id}"
