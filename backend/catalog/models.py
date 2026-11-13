from __future__ import annotations

from django.db import models

from core.models import TenantModel


class Unit(models.TextChoices):
    """How a service is counted. « invité » follows the wedding's guest count in quotes."""

    FLAT = "flat", "Forfait"
    UNIT = "unit", "Unité"
    GUEST = "guest", "Invité"
    DAY = "day", "Journée"
    EVENING = "evening", "Soirée"


class ServiceCategory(TenantModel):
    name = models.CharField(max_length=80)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta(TenantModel.Meta):
        ordering = ["order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"], name="unique_category_name_per_org"
            )
        ]

    def __str__(self) -> str:
        return self.name


class QuantityRule(models.TextChoices):
    """Quantity proposed when the service is added to a quote (complement §9)."""

    ONE = "one", "1"
    PER_GUEST = "per_guest", "Nombre d’invités"
    PER_TEN_GUESTS = "per_ten_guests", "1 pour 10 invités"


class ServiceItem(TenantModel):
    category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name="items")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=16, choices=Unit.choices, default=Unit.FLAT)
    unit_price = models.BigIntegerField()
    is_active = models.BooleanField(default=True)
    # « invité » units always follow the guest count; this rule covers the other units
    # (chairs = guests, centrepieces = one per table of ten).
    quantity_rule = models.CharField(
        max_length=16, choices=QuantityRule.choices, default=QuantityRule.ONE
    )
    # Added to every new quote (the prototype starts with three usual services).
    is_default = models.BooleanField(default=False)
    # Line icon on the quotes (documents.icons); blank = guessed from the name.
    icon = models.CharField(max_length=24, blank=True)

    class Meta(TenantModel.Meta):
        ordering = ["category__order", "name"]
        indexes = [models.Index(fields=["organization", "is_active"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(unit_price__gte=0), name="service_item_price_positive"
            )
        ]

    def __str__(self) -> str:
        return self.name
