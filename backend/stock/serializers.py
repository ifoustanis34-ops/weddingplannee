from __future__ import annotations

from typing import Any

from rest_framework import serializers

from core.fields import TenantPrimaryKeyRelatedField
from core.signed_files import signed_url

from .availability import Availability
from .models import (
    Inventory,
    InventoryLine,
    Item,
    ItemCategory,
    ItemUnit,
    Maintenance,
    Pack,
    PackComponent,
    StockMovement,
)
from .permissions import can_see_costs, can_see_prices, role_of


class MoneyAware:
    """Amounts never leave the server for a role that must not see them (§12)."""

    price_fields: tuple[str, ...] = ()
    cost_fields: tuple[str, ...] = ()
    context: dict[str, Any]

    def strip(self, data: dict[str, Any]) -> dict[str, Any]:
        role = role_of(self.context["request"]) if "request" in self.context else None
        hidden: tuple[str, ...] = ()
        if not can_see_prices(role):
            hidden += self.price_fields
        if not can_see_costs(role):
            hidden += self.cost_fields
        for key in hidden:
            if key in data:
                data[key] = None
        return data


class ItemCategorySerializer(serializers.ModelSerializer[ItemCategory]):
    class Meta:
        model = ItemCategory
        fields = ["id", "name", "cleaning_days", "position"]
        read_only_fields = ["id"]


class AvailabilitySerializer(serializers.Serializer[Availability]):
    total = serializers.IntegerField()
    available = serializers.IntegerField()
    reserved = serializers.IntegerField()
    out = serializers.IntegerField()
    maintenance = serializers.IntegerField()
    out_of_service = serializers.IntegerField()


class ItemSerializer(MoneyAware, serializers.ModelSerializer[Item]):
    price_fields = ("rent_price", "sale_price", "deposit")
    cost_fields = ("purchase_cost", "stock_value")

    category = TenantPrimaryKeyRelatedField(ItemCategory)
    category_name = serializers.CharField(source="category.name", read_only=True)
    photo_url = serializers.SerializerMethodField()
    today = serializers.SerializerMethodField()
    stock_value = serializers.SerializerMethodField()
    delay_days = serializers.IntegerField(read_only=True)
    reference = serializers.CharField(max_length=32, required=False, allow_blank=True)
    # Creation only: opening stock (a purchase movement) and the serials of numbered units.
    initial_quantity = serializers.IntegerField(min_value=0, required=False, write_only=True)
    serials = serializers.ListField(
        child=serializers.CharField(max_length=64), required=False, write_only=True
    )
    rent_price = serializers.IntegerField(min_value=0, required=False)
    sale_price = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    purchase_cost = serializers.IntegerField(min_value=0, required=False)
    deposit = serializers.IntegerField(min_value=0, required=False)

    class Meta:
        model = Item
        fields = [
            "id",
            "reference",
            "name",
            "category",
            "category_name",
            "photo_url",
            "description",
            "location",
            "tracking",
            "total_quantity",
            "rent_price",
            "rent_unit",
            "sale_price",
            "purchase_cost",
            "deposit",
            "alert_threshold",
            "cleaning_days",
            "delay_days",
            "is_active",
            "today",
            "stock_value",
            "initial_quantity",
            "serials",
            "created_at",
        ]
        read_only_fields = ["id", "total_quantity", "created_at"]

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Indiquez le nom de l’article.")
        return value

    def get_photo_url(self, item: Item) -> str | None:
        return signed_url(item.photo.name) if item.photo else None

    def get_today(self, item: Item) -> dict[str, int] | None:
        value = self.context.get("availability", {}).get(str(item.pk))
        return dict(AvailabilitySerializer(value).data) if value else None

    def get_stock_value(self, item: Item) -> int:
        return item.total_quantity * item.purchase_cost

    def to_representation(self, instance: Item) -> dict[str, Any]:
        return self.strip(dict(super().to_representation(instance)))


class ItemUnitSerializer(serializers.ModelSerializer[ItemUnit]):
    class Meta:
        model = ItemUnit
        fields = ["id", "serial_number", "status", "condition", "notes"]
        read_only_fields = ["id"]

    def validate_status(self, value: str) -> str:
        # Sold and lost come from a movement (it changes what the agency owns).
        if value in (ItemUnit.Status.SOLD, ItemUnit.Status.LOST, ItemUnit.Status.MAINTENANCE):
            raise serializers.ValidationError(
                "Utilisez une vente, une perte ou une maintenance pour ce changement."
            )
        return value


class PackComponentSerializer(serializers.ModelSerializer[PackComponent]):
    item = TenantPrimaryKeyRelatedField(Item)
    item_name = serializers.CharField(source="item.name", read_only=True)
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = PackComponent
        fields = ["item", "item_name", "quantity"]


class PackSerializer(MoneyAware, serializers.ModelSerializer[Pack]):
    price_fields = ("price",)

    components = PackComponentSerializer(many=True)
    price = serializers.IntegerField(min_value=0)
    available = serializers.SerializerMethodField()

    class Meta:
        model = Pack
        fields = ["id", "name", "description", "price", "is_active", "components", "available"]
        read_only_fields = ["id"]

    def get_available(self, pack: Pack) -> int | None:
        counts: dict[str, int] = self.context.get("pack_available", {})
        return counts.get(str(pack.pk))

    def to_representation(self, instance: Pack) -> dict[str, Any]:
        return self.strip(dict(super().to_representation(instance)))


class MovementSerializer(MoneyAware, serializers.ModelSerializer[StockMovement]):
    cost_fields = ("unit_cost",)

    item_name = serializers.CharField(source="item.name", read_only=True)
    item_reference = serializers.CharField(source="item.reference", read_only=True)
    serial_number = serializers.CharField(source="unit.serial_number", read_only=True, default=None)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    author_name = serializers.CharField(source="author.full_name", read_only=True, default=None)

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "item",
            "item_name",
            "item_reference",
            "unit",
            "serial_number",
            "kind",
            "kind_label",
            "delta",
            "quantity",
            "reason",
            "reference",
            "unit_cost",
            "author_name",
            "occurred_at",
            "cancelled_at",
            "cancel_reason",
        ]

    def to_representation(self, instance: StockMovement) -> dict[str, Any]:
        return self.strip(dict(super().to_representation(instance)))


class MovementInputSerializer(serializers.Serializer[Any]):
    item = TenantPrimaryKeyRelatedField(Item)
    unit = TenantPrimaryKeyRelatedField(ItemUnit, required=False, allow_null=True)
    kind = serializers.ChoiceField(
        choices=[
            ("purchase", "Achat"),
            ("sale", "Vente"),
            ("breakage", "Casse"),
            ("loss", "Perte"),
            ("adjustment", "Ajustement"),
        ]
    )
    quantity = serializers.IntegerField(min_value=1)
    direction = serializers.ChoiceField(choices=[1, -1], default=1)
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    reference = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    unit_cost = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    serials = serializers.ListField(child=serializers.CharField(max_length=64), required=False)


class CancelSerializer(serializers.Serializer[Any]):
    reason = serializers.CharField(max_length=255)


class MaintenanceSerializer(MoneyAware, serializers.ModelSerializer[Maintenance]):
    cost_fields = ("cost",)

    item = TenantPrimaryKeyRelatedField(Item)
    unit = TenantPrimaryKeyRelatedField(ItemUnit, required=False, allow_null=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    serial_number = serializers.CharField(source="unit.serial_number", read_only=True, default=None)
    is_late = serializers.SerializerMethodField()

    class Meta:
        model = Maintenance
        fields = [
            "id",
            "item",
            "item_name",
            "unit",
            "serial_number",
            "quantity",
            "reason",
            "started_at",
            "expected_end",
            "ended_at",
            "cost",
            "is_late",
        ]
        read_only_fields = ["id", "started_at", "ended_at", "cost"]

    def get_is_late(self, maintenance: Maintenance) -> bool:
        from django.utils import timezone

        return bool(
            maintenance.ended_at is None
            and maintenance.expected_end
            and maintenance.expected_end < timezone.localdate()
        )

    def to_representation(self, instance: Maintenance) -> dict[str, Any]:
        return self.strip(dict(super().to_representation(instance)))


class CloseMaintenanceSerializer(serializers.Serializer[Any]):
    cost = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class InventoryLineSerializer(serializers.ModelSerializer[InventoryLine]):
    item_name = serializers.CharField(source="item.name", read_only=True)
    item_reference = serializers.CharField(source="item.reference", read_only=True)
    category_name = serializers.CharField(source="item.category.name", read_only=True)
    difference = serializers.IntegerField(read_only=True)

    class Meta:
        model = InventoryLine
        fields = [
            "id",
            "item",
            "item_name",
            "item_reference",
            "category_name",
            "expected",
            "counted",
            "difference",
        ]


class InventorySerializer(serializers.ModelSerializer[Inventory]):
    category = TenantPrimaryKeyRelatedField(ItemCategory, required=False, allow_null=True)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    author_name = serializers.CharField(source="author.full_name", read_only=True, default=None)
    lines = InventoryLineSerializer(many=True, read_only=True)

    class Meta:
        model = Inventory
        fields = [
            "id",
            "date",
            "category",
            "category_name",
            "status",
            "author_name",
            "validated_at",
            "lines",
        ]
        read_only_fields = ["id", "date", "status", "validated_at"]


class CountSerializer(serializers.Serializer[Any]):
    counts = serializers.DictField(
        child=serializers.IntegerField(min_value=0, allow_null=True), allow_empty=False
    )
