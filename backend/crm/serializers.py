from __future__ import annotations

from typing import Any

from rest_framework import serializers

from finance.visibility import can_see_balances

from .models import Client

MONEY_FIELDS = ("revenue", "collected", "balance_due")


def _role(context: dict[str, Any]) -> str | None:
    request = context.get("request")
    membership = getattr(request, "membership", None)
    return membership.role if membership is not None else None


class ClientSerializer(serializers.ModelSerializer[Client]):
    # Annotated by ``selectors.with_metrics`` (list and detail).
    order_count = serializers.IntegerField(read_only=True, default=0)
    revenue = serializers.IntegerField(read_only=True, default=0)
    collected = serializers.IntegerField(read_only=True, default=0)
    balance_due = serializers.IntegerField(read_only=True, default=0)
    last_order_at = serializers.DateTimeField(read_only=True, default=None)

    class Meta:
        model = Client
        fields = [
            "id",
            "name",
            "company",
            "phone",
            "phone_alt",
            "email",
            "address",
            "notes",
            "preferences",
            "is_archived",
            "order_count",
            "revenue",
            "collected",
            "balance_due",
            "last_order_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Indiquez le nom du client ou du couple.")
        return value

    def to_representation(self, instance: Client) -> dict[str, Any]:
        data = dict(super().to_representation(instance))
        if not can_see_balances(_role(self.context)):
            for key in MONEY_FIELDS:
                data[key] = None
        return data


class ClientSummarySerializer(serializers.ModelSerializer[Client]):
    """Nested in quotes and contracts."""

    class Meta:
        model = Client
        fields = ["id", "name", "company", "phone", "email"]


class HistoryQuoteSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    number = serializers.CharField()
    status = serializers.CharField()
    issue_date = serializers.DateField()
    total = serializers.IntegerField()


class HistoryContractSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    number = serializers.CharField()
    status = serializers.CharField()
    signed_at = serializers.DateTimeField()
    wedding_date = serializers.DateField(allow_null=True)
    total = serializers.IntegerField()


class HistoryReservationSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    number = serializers.CharField()
    title = serializers.CharField()
    status = serializers.CharField()
    event_start = serializers.DateTimeField()
    total = serializers.IntegerField()
    balance = serializers.IntegerField()


class HistoryPaymentSerializer(serializers.Serializer[Any]):
    id = serializers.UUIDField()
    origin = serializers.ChoiceField(choices=["contract", "reservation"])
    reference = serializers.CharField()
    kind = serializers.CharField()
    amount = serializers.IntegerField()
    method = serializers.CharField()
    paid_at = serializers.DateField()
    is_cancelled = serializers.BooleanField()


class ClientHistorySerializer(serializers.Serializer[Any]):
    reservations = HistoryReservationSerializer(many=True)
    quotes = HistoryQuoteSerializer(many=True)
    contracts = HistoryContractSerializer(many=True)
    payments = HistoryPaymentSerializer(many=True)
