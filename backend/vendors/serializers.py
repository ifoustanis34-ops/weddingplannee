from __future__ import annotations

from typing import Any

from rest_framework import serializers

from core.fields import TenantPrimaryKeyRelatedField

from .models import Vendor, VendorAssignment

MONEY_FIELDS = ("cost", "paid_amount", "due")


class VendorSerializer(serializers.ModelSerializer[Vendor]):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    collaborations = serializers.IntegerField(read_only=True, default=0)
    due = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Vendor
        fields = [
            "id",
            "name",
            "kind",
            "kind_label",
            "category",
            "category_label",
            "contact_name",
            "phone",
            "whatsapp",
            "email",
            "city",
            "address",
            "tax_id",
            "trade_register",
            "payment_terms",
            "mobile_money",
            "bank_details",
            "services",
            "notes",
            "collaborations",
            "due",
        ]
        read_only_fields = ["id"]

    def validate_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Indiquez le nom.")
        return value.strip()


class AssignmentSerializer(serializers.ModelSerializer[VendorAssignment]):
    vendor = TenantPrimaryKeyRelatedField(Vendor)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    vendor_category_label = serializers.CharField(
        source="vendor.get_category_display", read_only=True
    )
    vendor_phone = serializers.CharField(source="vendor.phone", read_only=True)
    wedding_title = serializers.CharField(source="wedding.title", read_only=True)
    due = serializers.IntegerField(read_only=True)

    class Meta:
        model = VendorAssignment
        fields = [
            "id",
            "wedding",
            "wedding_title",
            "vendor",
            "vendor_name",
            "vendor_category_label",
            "vendor_phone",
            "service",
            "cost",
            "paid_amount",
            "due",
        ]
        read_only_fields = ["id", "wedding"]

    def validate_vendor(self, value: Vendor) -> Vendor:
        if value.is_deleted:
            raise serializers.ValidationError("Ce contact a été supprimé du carnet.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        cost = attrs.get("cost", self.instance.cost if self.instance else 0)
        paid = attrs.get("paid_amount", self.instance.paid_amount if self.instance else 0)
        if cost < 0 or paid < 0:
            raise serializers.ValidationError({"cost": ["Les montants sont positifs."]})
        if paid > cost:
            raise serializers.ValidationError(
                {"paid_amount": ["Le montant payé dépasse le coût de la prestation."]}
            )
        return attrs


def strip_money(data: dict[str, Any]) -> dict[str, Any]:
    """Roles without access to money (assistant) see who works on the wedding, not the cost."""
    return {key: value for key, value in data.items() if key not in MONEY_FIELDS}
