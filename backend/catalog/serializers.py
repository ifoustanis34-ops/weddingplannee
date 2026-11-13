from __future__ import annotations

from rest_framework import serializers

from core.fields import TenantPrimaryKeyRelatedField

from .models import ServiceCategory, ServiceItem


class ServiceItemSerializer(serializers.ModelSerializer[ServiceItem]):
    unit_label = serializers.CharField(source="get_unit_display", read_only=True)
    unit_price = serializers.IntegerField(min_value=0)
    category = TenantPrimaryKeyRelatedField(ServiceCategory)

    class Meta:
        model = ServiceItem
        fields = [
            "id",
            "category",
            "name",
            "description",
            "unit",
            "unit_label",
            "unit_price",
            "is_active",
            "quantity_rule",
            "is_default",
            "icon",
        ]

    def validate_icon(self, value: str) -> str:
        from documents.icons import SERVICE_ICONS

        if value and value not in SERVICE_ICONS:
            raise serializers.ValidationError("Icône inconnue.")
        return value


class ServiceCategorySerializer(serializers.ModelSerializer[ServiceCategory]):
    items = ServiceItemSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceCategory
        fields = ["id", "name", "order", "items"]
