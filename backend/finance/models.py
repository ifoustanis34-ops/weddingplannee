from __future__ import annotations

import uuid
from typing import Any

from django.db import models

from core.models import TenantModel


def receipt_path(instance: Expense, filename: str) -> str:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"org/{instance.organization_id}/finance/receipts/{uuid.uuid4().hex}.{extension}"


class ExpenseCategory(TenantModel):
    """Expense categories (reservations-stock.md §6.2), editable by each agency."""

    name = models.CharField(max_length=80)
    position = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta(TenantModel.Meta):
        ordering = ["position", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"], name="unique_expense_category_name"
            )
        ]

    def __str__(self) -> str:
        return self.name


class Expense(TenantModel):
    """An expense of the agency: attached to a wedding (its margin) or general (rent, fuel…)."""

    class Method(models.TextChoices):
        TRANSFER = "transfer", "Virement"
        CASH = "cash", "Espèces"
        ORANGE_MONEY = "orange_money", "Orange Money"
        MTN_MOMO = "mtn_momo", "MTN MoMo"
        WAVE = "wave", "Wave"
        CHEQUE = "cheque", "Chèque"

    wedding = models.ForeignKey(
        "events.Wedding",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="expenses",
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="expenses",
    )
    # §6.2: an expense may belong to a reservation (its profitability).
    reservation = models.ForeignKey(
        "reservations.Reservation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
    )
    # Photo or PDF of the receipt (§6.2): private, served by signed URL only.
    receipt = models.FileField(upload_to=receipt_path, blank=True)
    label = models.CharField(max_length=160)
    amount = models.BigIntegerField()
    date = models.DateField(null=True, blank=True)
    supplier = models.CharField(max_length=160, blank=True)
    method = models.CharField(max_length=16, choices=Method.choices, blank=True)
    is_paid = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta(TenantModel.Meta):
        ordering = ["date", "created_at"]
        indexes = [
            models.Index(fields=["organization", "wedding"]),
            models.Index(fields=["organization", "date"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=0), name="expense_amount_positive"
            )
        ]

    def __str__(self) -> str:
        return self.label

    def save(self, *args: Any, **kwargs: Any) -> None:
        # A wedding cost without a category is a vendor cost: « Sous-traitance » (same rule as the
        # data migration), so every expense lands in the ring of the dashboard.
        if self.category_id is None and (
            self.wedding is not None or self.reservation_id is not None
        ):
            from .defaults import SUBCONTRACTING

            owner = self.wedding if self.wedding is not None else self.reservation
            organization_id = self.organization_id or owner.organization_id  # type: ignore[union-attr]
            self.category = ExpenseCategory._base_manager.filter(
                organization_id=organization_id, name=SUBCONTRACTING
            ).first()
        super().save(*args, **kwargs)


class RevenueCategory(models.TextChoices):
    RENTAL = "rental", "Location"
    SALE = "sale", "Vente"
    SERVICE = "service", "Prestation"
    TRANSPORT = "transport", "Transport"
    DAMAGE = "damage", "Casse et pertes"


class Revenue(TenantModel):
    """Money received (§6.1), created by every payment and split by category; a cancelled
    payment cancels its revenues (never deleted). The security deposit is not revenue."""

    amount = models.BigIntegerField()
    date = models.DateField()
    category = models.CharField(max_length=16, choices=RevenueCategory.choices)
    label = models.CharField(max_length=160)
    method = models.CharField(max_length=16, blank=True)
    client = models.ForeignKey(
        "crm.Client", on_delete=models.PROTECT, null=True, blank=True, related_name="revenues"
    )
    reservation = models.ForeignKey(
        "reservations.Reservation",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revenues",
    )
    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revenues",
    )
    reservation_payment = models.ForeignKey(
        "reservations.ReservationPayment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revenues",
    )
    contract_payment = models.ForeignKey(
        "contracts.Payment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revenues",
    )
    is_cancelled = models.BooleanField(default=False)

    class Meta(TenantModel.Meta):
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["organization", "date"]),
            models.Index(fields=["organization", "category"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=0), name="revenue_amount_positive"
            )
        ]

    def __str__(self) -> str:
        return self.label


class Invoice(TenantModel):
    """Deposit or final invoice of a reservation (§6.3), frozen at issue: its lines and its
    document snapshot never change. Cancelled only by credit notes."""

    class Kind(models.TextChoices):
        DEPOSIT = "deposit", "Facture d’acompte"
        FINAL = "final", "Facture"

    number = models.CharField(max_length=32)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    reservation = models.ForeignKey(
        "reservations.Reservation", on_delete=models.PROTECT, related_name="invoices"
    )
    client = models.ForeignKey("crm.Client", on_delete=models.PROTECT, related_name="invoices")
    issued_at = models.DateField()
    due_at = models.DateField()
    total = models.BigIntegerField()
    snapshot = models.JSONField(default=dict)

    class Meta(TenantModel.Meta):
        ordering = ["-issued_at", "-number"]
        indexes = [models.Index(fields=["organization", "issued_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "number"], name="unique_invoice_number"
            ),
            models.CheckConstraint(condition=models.Q(total__gte=0), name="invoice_total_positive"),
        ]

    def __str__(self) -> str:
        return self.number


class InvoiceLine(TenantModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    label = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.BigIntegerField()
    amount = models.BigIntegerField()
    category = models.CharField(max_length=16, choices=RevenueCategory.choices, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta(TenantModel.Meta):
        ordering = ["position"]

    def __str__(self) -> str:
        return self.label


class CreditNote(TenantModel):
    """« Avoir »: cancels all or part of an invoice (§6.3), numbered without gaps."""

    number = models.CharField(max_length=32)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="credit_notes")
    reservation = models.ForeignKey(
        "reservations.Reservation", on_delete=models.PROTECT, related_name="credit_notes"
    )
    client = models.ForeignKey("crm.Client", on_delete=models.PROTECT, related_name="credit_notes")
    issued_at = models.DateField()
    amount = models.BigIntegerField()
    reason = models.CharField(max_length=255)
    snapshot = models.JSONField(default=dict)

    class Meta(TenantModel.Meta):
        ordering = ["-issued_at", "-number"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "number"], name="unique_credit_note_number"
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="credit_note_amount_positive"
            ),
        ]

    def __str__(self) -> str:
        return self.number
