from __future__ import annotations

from datetime import date
from typing import Any

from django.utils import timezone
from rest_framework import serializers

from finance.visibility import can_see_margins

from .models import Contract, Payment
from .services import allocate


class PaymentSerializer(serializers.ModelSerializer[Payment]):
    method_label = serializers.CharField(source="get_method_display", read_only=True)
    recorded_by_name = serializers.CharField(
        source="recorded_by.full_name", read_only=True, default=None
    )
    has_receipt = serializers.SerializerMethodField()
    has_proof = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id",
            "amount",
            "method",
            "method_label",
            "paid_at",
            "reference",
            "receipt_number",
            "has_receipt",
            "has_proof",
            "recorded_by_name",
            "is_cancelled",
            "cancelled_at",
            "cancel_reason",
            "created_at",
        ]
        read_only_fields = fields

    def get_has_receipt(self, payment: Payment) -> bool:
        return not payment.is_cancelled

    def get_has_proof(self, payment: Payment) -> bool:
        return bool(payment.proof)


class PaymentInputSerializer(serializers.Serializer[Any]):
    amount = serializers.IntegerField(min_value=1)
    method = serializers.ChoiceField(choices=Payment.Method.choices)
    paid_at = serializers.DateField(default=timezone.localdate)
    reference = serializers.CharField(required=False, allow_blank=True, default="", max_length=120)
    proof = serializers.FileField(required=False, allow_null=True)

    def validate_proof(self, value: Any) -> Any:
        if value is None:
            return value
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Justificatif trop lourd : 5 Mo maximum.")
        name = (value.name or "").lower()
        if not name.endswith((".pdf", ".jpg", ".jpeg", ".png", ".webp", ".heic")):
            raise serializers.ValidationError("Formats acceptés : PDF, JPG, PNG, WEBP, HEIC.")
        return value


class CancelPaymentSerializer(serializers.Serializer[Any]):
    reason = serializers.CharField(allow_blank=True)


class InstallmentSerializer(serializers.Serializer[Any]):
    def get_fields(self) -> dict[str, serializers.Field[Any, Any, Any, Any]]:
        # Declared here: a `label` class attribute would shadow Field.label.
        return {
            "label": serializers.CharField(max_length=80, allow_blank=True, default=""),
            "amount": serializers.IntegerField(min_value=1),
            "due_date": serializers.DateField(),
        }


class ScheduleInputSerializer(serializers.Serializer[Any]):
    installments = InstallmentSerializer(many=True)


def _hide_margins(data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    if not can_see_margins(context.get("role")):
        for key in ("expenses", "margin", "margin_pct", "expense_items"):
            data.pop(key, None)
    return data


class ContractListSerializer(serializers.ModelSerializer[Contract]):
    client_name = serializers.CharField(source="client.name", read_only=True)
    client = serializers.UUIDField(source="client_id", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    collected = serializers.IntegerField(read_only=True)
    balance = serializers.IntegerField(read_only=True)
    expenses = serializers.IntegerField(read_only=True)
    margin = serializers.IntegerField(read_only=True)
    margin_pct = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    wedding = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = [
            "id",
            "number",
            "client",
            "client_name",
            "wedding_date",
            "wedding",
            "total",
            "collected",
            "balance",
            "expenses",
            "margin",
            "margin_pct",
            "progress",
            "status",
            "status_label",
            "signed_at",
        ]

    def get_margin_pct(self, contract: Contract) -> float | None:
        margin = getattr(contract, "margin", None)
        return (
            round(margin * 100 / contract.total, 1)
            if contract.total and margin is not None
            else None
        )

    def get_progress(self, contract: Contract) -> int:
        collected = getattr(contract, "collected", 0)
        return round(collected * 100 / contract.total) if contract.total else 0

    def get_wedding(self, contract: Contract) -> str | None:
        wedding = getattr(contract, "wedding", None)
        return str(wedding.pk) if wedding else None

    def to_representation(self, instance: Contract) -> dict[str, Any]:
        return _hide_margins(dict(super().to_representation(instance)), self.context)


class ContractDetailSerializer(ContractListSerializer):
    schedule = serializers.SerializerMethodField()
    payments = PaymentSerializer(many=True, read_only=True)
    expense_items = serializers.SerializerMethodField()
    quote = serializers.SerializerMethodField()
    client_email = serializers.CharField(source="client.email", read_only=True)
    client_phone = serializers.CharField(source="client.phone", read_only=True)

    class Meta(ContractListSerializer.Meta):
        fields = [
            *ContractListSerializer.Meta.fields,
            "client_email",
            "client_phone",
            "quote",
            "schedule",
            "payments",
            "expense_items",
        ]

    def get_schedule(self, contract: Contract) -> list[dict[str, Any]]:
        today = date.today()
        return [
            {
                "id": str(a.schedule.pk),
                "label": a.schedule.label,
                "amount": a.schedule.amount,
                "due_date": a.schedule.due_date,
                "paid": a.paid,
                "remaining": a.remaining,
                "is_paid": a.remaining == 0,
                "is_overdue": a.remaining > 0 and a.schedule.due_date < today,
            }
            for a in allocate(contract)
        ]

    def get_expense_items(self, contract: Contract) -> list[dict[str, Any]]:
        wedding = getattr(contract, "wedding", None)
        if wedding is None:
            return []
        return [
            {
                "id": str(e.pk),
                "label": e.label,
                "amount": e.amount,
                "date": e.date,
                "is_paid": e.is_paid,
            }
            for e in wedding.expenses.all()
        ]

    def get_quote(self, contract: Contract) -> dict[str, str]:
        return {"id": str(contract.quote_id), "number": contract.quote.number}
