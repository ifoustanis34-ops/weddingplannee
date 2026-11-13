from __future__ import annotations

from typing import Any

from rest_framework import serializers

from core.fields import TenantPrimaryKeyRelatedField
from core.signed_files import signed_url
from events.models import Wedding
from reservations.models import Reservation

from .models import Expense, ExpenseCategory


class ExpenseCategorySerializer(serializers.ModelSerializer[ExpenseCategory]):
    class Meta:
        model = ExpenseCategory
        fields = ["id", "name", "position", "is_active"]
        read_only_fields = ["id"]

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Indiquez le nom de la catégorie.")
        duplicates = ExpenseCategory.objects.filter(name__iexact=value)
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("Cette catégorie existe déjà.")
        return value


class ExpenseSerializer(serializers.ModelSerializer[Expense]):
    """A wedding expense (its margin) or a general one (no wedding: rent, fuel, marketing…)."""

    wedding = TenantPrimaryKeyRelatedField(Wedding, allow_null=True, required=False)
    category = TenantPrimaryKeyRelatedField(ExpenseCategory, allow_null=True, required=False)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    wedding_title = serializers.CharField(source="wedding.title", read_only=True, default=None)
    reservation = TenantPrimaryKeyRelatedField(Reservation, allow_null=True, required=False)
    reservation_number = serializers.CharField(
        source="reservation.number", read_only=True, default=None
    )
    receipt_url = serializers.SerializerMethodField()
    amount = serializers.IntegerField(min_value=1)
    method = serializers.ChoiceField(
        choices=Expense.Method.choices, required=False, allow_blank=True
    )

    class Meta:
        model = Expense
        fields = [
            "id",
            "wedding",
            "wedding_title",
            "reservation",
            "reservation_number",
            "receipt_url",
            "category",
            "category_name",
            "label",
            "amount",
            "date",
            "supplier",
            "method",
            "is_paid",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        # A general expense has no wedding to explain it: its category is required.
        wedding = attrs.get("wedding", getattr(self.instance, "wedding", None))
        reservation = attrs.get("reservation", getattr(self.instance, "reservation", None))
        category = attrs.get("category", getattr(self.instance, "category", None))
        if wedding is None and reservation is None and category is None:
            raise serializers.ValidationError(
                {"category": ["Choisissez la catégorie de cette dépense."]}
            )
        return attrs

    def get_receipt_url(self, expense: Expense) -> str | None:
        return signed_url(expense.receipt.name) if expense.receipt else None
