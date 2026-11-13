"""Stock and equipment (docs/specs/reservations-stock.md §5). Amounts are integer FCFA."""

from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.db import models
from django.db.models import Q

from core.models import TenantModel


def photo_path(instance: Any, filename: str) -> str:
    """Photos live under the agency's prefix; the name never comes from the upload."""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"org/{instance.organization_id}/stock/{uuid.uuid4().hex}.{extension}"


class ItemCategory(TenantModel):
    """Mobilier, linge de table… with the cleaning delay after each return (e.g. linen: 1 day)."""

    name = models.CharField(max_length=80)
    cleaning_days = models.PositiveSmallIntegerField(default=0)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta(TenantModel.Meta):
        ordering = ["position", "name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="unique_item_category")
        ]

    def __str__(self) -> str:
        return self.name


class Item(TenantModel):
    class Tracking(models.TextChoices):
        QUANTITY = "quantity", "Par quantité"
        UNIT = "unit", "Par unité (numéro de série)"

    class RentUnit(models.TextChoices):
        DAY = "day", "Par jour"
        EVENT = "event", "Par événement"

    reference = models.CharField(max_length=32)
    name = models.CharField(max_length=160)
    category = models.ForeignKey(ItemCategory, on_delete=models.PROTECT, related_name="items")
    photo = models.FileField(upload_to=photo_path, blank=True)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=80, blank=True)  # place in the warehouse
    tracking = models.CharField(max_length=16, choices=Tracking.choices, default=Tracking.QUANTITY)
    # Owned quantity. Kept by the movements (purchase, sale, loss…); for unit-tracked items it
    # counts the units still owned (not sold, not lost).
    total_quantity = models.PositiveIntegerField(default=0)
    rent_price = models.BigIntegerField(default=0)
    rent_unit = models.CharField(max_length=8, choices=RentUnit.choices, default=RentUnit.EVENT)
    sale_price = models.BigIntegerField(null=True, blank=True)
    purchase_cost = models.BigIntegerField(default=0)
    deposit = models.BigIntegerField(default=0)
    alert_threshold = models.PositiveIntegerField(default=0)
    # Overrides the category's cleaning delay when set.
    cleaning_days = models.PositiveSmallIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta(TenantModel.Meta):
        ordering = ["category__position", "name"]
        indexes = [models.Index(fields=["organization", "category"])]
        constraints = [
            models.UniqueConstraint(fields=["organization", "reference"], name="unique_item_ref"),
            models.CheckConstraint(
                condition=Q(rent_price__gte=0, purchase_cost__gte=0, deposit__gte=0)
                & (Q(sale_price__isnull=True) | Q(sale_price__gte=0)),
                name="item_amounts_positive",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def delay_days(self) -> int:
        """Cleaning delay after a return (item override, else its category)."""
        if self.cleaning_days is not None:
            return self.cleaning_days
        return self.category.cleaning_days


class ItemUnit(TenantModel):
    """One numbered piece of a unit-tracked item (sound system, generator, projector)."""

    class Status(models.TextChoices):
        AVAILABLE = "available", "Disponible"
        MAINTENANCE = "maintenance", "En maintenance"
        OUT_OF_SERVICE = "out_of_service", "Hors service"
        LOST = "lost", "Perdu"
        SOLD = "sold", "Vendu"

    class Condition(models.TextChoices):
        GOOD = "good", "Bon état"
        WORN = "worn", "Usé"
        DAMAGED = "damaged", "Abîmé"

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="units")
    serial_number = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.AVAILABLE)
    condition = models.CharField(max_length=8, choices=Condition.choices, default=Condition.GOOD)
    notes = models.TextField(blank=True)

    class Meta(TenantModel.Meta):
        ordering = ["serial_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "item", "serial_number"], name="unique_item_serial"
            )
        ]

    def __str__(self) -> str:
        return f"{self.item} {self.serial_number}"


class Pack(TenantModel):
    """Ready-to-book set (« Pack réception 100 invités »), available when all its parts are."""

    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    price = models.BigIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta(TenantModel.Meta):
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(condition=Q(price__gte=0), name="pack_price_positive")
        ]

    def __str__(self) -> str:
        return self.name


class PackComponent(TenantModel):
    pack = models.ForeignKey(Pack, on_delete=models.CASCADE, related_name="components")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="+")
    quantity = models.PositiveIntegerField()

    class Meta(TenantModel.Meta):
        ordering = ["item__name"]
        constraints = [
            models.UniqueConstraint(fields=["pack", "item"], name="unique_pack_item"),
            models.CheckConstraint(condition=Q(quantity__gt=0), name="pack_quantity_positive"),
        ]


class StockMovement(TenantModel):
    """Immutable journal (§5.3): never edited or deleted, only cancelled with a reason."""

    class Kind(models.TextChoices):
        PURCHASE = "purchase", "Achat"
        CHECKOUT = "checkout", "Sortie pour réservation"
        RETURN = "return", "Retour"
        SALE = "sale", "Vente"
        BREAKAGE = "breakage", "Casse"
        LOSS = "loss", "Perte"
        MAINTENANCE_OUT = "maintenance_out", "Envoi en maintenance"
        MAINTENANCE_IN = "maintenance_in", "Retour de maintenance"
        ADJUSTMENT = "adjustment", "Ajustement d’inventaire"

    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="movements")
    unit = models.ForeignKey(
        ItemUnit, on_delete=models.PROTECT, null=True, blank=True, related_name="movements"
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    # Signed effect on the owned quantity (+ purchase, − sale/breakage/loss, ± adjustment; 0 for
    # checkouts, returns and maintenance, which do not change what the agency owns).
    delta = models.IntegerField(default=0)
    quantity = models.PositiveIntegerField()
    reason = models.CharField(max_length=255, blank=True)
    reference = models.CharField(max_length=80, blank=True)  # purchase invoice, reservation…
    unit_cost = models.BigIntegerField(null=True, blank=True)  # purchases
    # A purchase creates its expense (§6.1); cancelling the purchase removes it.
    expense = models.ForeignKey(
        "finance.Expense", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    occurred_at = models.DateTimeField()
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=255, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta(TenantModel.Meta):
        ordering = ["-occurred_at", "-created_at"]
        indexes = [
            models.Index(fields=["organization", "item", "-occurred_at"]),
            models.Index(fields=["organization", "kind"]),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name="movement_quantity_positive")
        ]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} — {self.item_id} × {self.quantity}"


class Maintenance(TenantModel):
    """Equipment away for repair: unavailable from ``started_at`` until it comes back."""

    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="maintenances")
    unit = models.ForeignKey(
        ItemUnit, on_delete=models.PROTECT, null=True, blank=True, related_name="maintenances"
    )
    quantity = models.PositiveIntegerField(default=1)
    reason = models.CharField(max_length=255)
    started_at = models.DateField()
    expected_end = models.DateField(null=True, blank=True)
    ended_at = models.DateField(null=True, blank=True)
    cost = models.BigIntegerField(null=True, blank=True)
    expense = models.ForeignKey(
        "finance.Expense", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta(TenantModel.Meta):
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["organization", "ended_at"])]
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name="maintenance_quantity_pos"),
            models.CheckConstraint(
                condition=Q(cost__isnull=True) | Q(cost__gte=0), name="maintenance_cost_positive"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.item} — {self.reason}"


class Inventory(TenantModel):
    """Physical count (§5.3): differences become adjustments once validated."""

    class Status(models.TextChoices):
        DRAFT = "draft", "En cours"
        VALIDATED = "validated", "Validé"

    date = models.DateField()
    category = models.ForeignKey(
        ItemCategory, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta(TenantModel.Meta):
        ordering = ["-date", "-created_at"]


class InventoryLine(TenantModel):
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="+")
    expected = models.PositiveIntegerField()
    counted = models.PositiveIntegerField(null=True, blank=True)

    class Meta(TenantModel.Meta):
        ordering = ["item__category__position", "item__name"]
        constraints = [
            models.UniqueConstraint(fields=["inventory", "item"], name="unique_inventory_item")
        ]

    @property
    def difference(self) -> int | None:
        return None if self.counted is None else self.counted - self.expected
