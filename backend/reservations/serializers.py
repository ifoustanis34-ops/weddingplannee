from __future__ import annotations

from typing import Any

from rest_framework import serializers

from accounts.models import User
from catalog.models import ServiceItem
from core.fields import TenantPrimaryKeyRelatedField
from crm.models import Client
from events.models import Wedding
from finance.visibility import can_see_balances
from stock.models import Item, Pack

from . import services
from .models import Reservation, ReservationLine, ReservationLog, ReservationPayment
from .permissions import role_of

MONEY = (
    "unit_price",
    "amount",
    "deposit",
    "subtotal",
    "total",
    "discount",
    "transport_fee",
    "setup_fee",
    "deposit_required",
    "security_deposit",
    "security_retained",
    "paid",
    "balance",
    "refund_due",
)


def strip(data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Amounts never reach the assistant or the storekeeper (§12)."""
    request = context.get("request")
    if request is None or can_see_balances(role_of(request)):
        return data
    for key in MONEY:
        if key in data:
            data[key] = None
    if "lines" in data:
        data["lines"] = [strip(dict(line), context) for line in data["lines"]]
    if "payments" in data:
        data["payments"] = []
    return data


class LineSerializer(serializers.ModelSerializer[ReservationLine]):
    item = TenantPrimaryKeyRelatedField(Item, required=False, allow_null=True)
    pack = TenantPrimaryKeyRelatedField(Pack, required=False, allow_null=True)
    service = TenantPrimaryKeyRelatedField(ServiceItem, required=False, allow_null=True)
    item_reference = serializers.CharField(source="item.reference", read_only=True, default=None)
    rent_unit = serializers.CharField(source="item.rent_unit", read_only=True, default=None)
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    deposit = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    period_days = serializers.IntegerField(min_value=1, required=False, default=1)
    kind = serializers.ChoiceField(
        choices=[c for c in ReservationLine.Kind.choices if c[0] != "damage"]
    )

    class Meta:
        model = ReservationLine
        fields = [
            "id",
            "kind",
            "item",
            "item_reference",
            "rent_unit",
            "pack",
            "service",
            "label",
            "quantity",
            "unit_price",
            "period_days",
            "deposit",
            "amount",
            "quantity_out",
            "quantity_returned",
            "quantity_damaged",
            "quantity_missing",
        ]
        read_only_fields = [
            "id",
            "amount",
            "quantity_out",
            "quantity_returned",
            "quantity_damaged",
            "quantity_missing",
        ]
        extra_kwargs = {"label": {"required": False, "allow_blank": True}}

    def to_representation(self, instance: ReservationLine) -> dict[str, Any]:
        data = dict(super().to_representation(instance))
        data["kind"] = instance.kind  # damage lines are shown too
        return data


class PaymentSerializer(serializers.ModelSerializer[ReservationPayment]):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    method_label = serializers.CharField(source="get_method_display", read_only=True)
    recorded_by_name = serializers.CharField(
        source="recorded_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = ReservationPayment
        fields = [
            "id",
            "kind",
            "kind_label",
            "amount",
            "method",
            "method_label",
            "paid_at",
            "reference",
            "recorded_by_name",
            "is_cancelled",
            "cancel_reason",
        ]


class LogSerializer(serializers.ModelSerializer[ReservationLog]):
    author_name = serializers.CharField(source="author.full_name", read_only=True, default=None)

    class Meta:
        model = ReservationLog
        fields = ["id", "action", "message", "author_name", "created_at"]


class ReservationListSerializer(serializers.ModelSerializer[Reservation]):
    client_name = serializers.CharField(source="client.name", read_only=True)
    owner_name = serializers.CharField(source="owner.full_name", read_only=True, default=None)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    paid = serializers.IntegerField(read_only=True, default=0)
    balance = serializers.IntegerField(read_only=True, default=0)
    next_step = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = [
            "id",
            "number",
            "client",
            "client_name",
            "kind",
            "title",
            "venue",
            "status",
            "status_label",
            "owner",
            "owner_name",
            "event_start",
            "event_end",
            "delivery_at",
            "total",
            "paid",
            "balance",
            "next_step",
        ]

    def get_next_step(self, reservation: Reservation) -> dict[str, Any] | None:
        return services.next_step(reservation)

    def to_representation(self, instance: Reservation) -> dict[str, Any]:
        return strip(dict(super().to_representation(instance)), self.context)


class ReservationSerializer(serializers.ModelSerializer[Reservation]):
    client = TenantPrimaryKeyRelatedField(Client, filters={"is_deleted": False})
    wedding = TenantPrimaryKeyRelatedField(Wedding, required=False, allow_null=True)
    owner = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )
    client_detail = serializers.SerializerMethodField()
    owner_name = serializers.CharField(source="owner.full_name", read_only=True, default=None)
    wedding_title = serializers.CharField(source="wedding.title", read_only=True, default=None)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    lines = LineSerializer(many=True)
    payments = PaymentSerializer(many=True, read_only=True)
    logs = LogSerializer(many=True, read_only=True)
    paid = serializers.IntegerField(read_only=True, default=0)
    balance = serializers.IntegerField(read_only=True, default=0)
    next_step = serializers.SerializerMethodField()
    discount = serializers.IntegerField(min_value=0, required=False)
    transport_fee = serializers.IntegerField(min_value=0, required=False)
    setup_fee = serializers.IntegerField(min_value=0, required=False)
    deposit_required = serializers.IntegerField(min_value=0, required=False)
    deposit_pct = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=100,
        required=False,
        write_only=True,
    )

    class Meta:
        model = Reservation
        fields = [
            "id",
            "number",
            "client",
            "client_detail",
            "wedding",
            "wedding_title",
            "kind",
            "title",
            "venue",
            "address",
            "guest_count",
            "owner",
            "owner_name",
            "status",
            "status_label",
            "delivery_at",
            "setup_at",
            "event_start",
            "event_end",
            "teardown_at",
            "pickup_at",
            "return_at",
            "vehicle",
            "discount",
            "transport_fee",
            "setup_fee",
            "subtotal",
            "total",
            "deposit_required",
            "deposit_pct",
            "security_deposit",
            "security_status",
            "security_retained",
            "paid",
            "balance",
            "refund_due",
            "notes",
            "confirmed_at",
            "checked_out_at",
            "returned_at",
            "cancelled_at",
            "cancel_reason",
            "next_step",
            "lines",
            "payments",
            "logs",
            "created_at",
        ]
        read_only_fields = [
            "number",
            "status",
            "subtotal",
            "total",
            "security_deposit",
            "security_status",
            "security_retained",
            "refund_due",
            "confirmed_at",
            "checked_out_at",
            "returned_at",
            "cancelled_at",
            "cancel_reason",
            "created_at",
        ]

    def get_client_detail(self, reservation: Reservation) -> dict[str, str]:
        client = reservation.client
        return {
            "id": str(client.pk),
            "name": client.name,
            "phone": client.phone,
            "email": client.email,
        }

    def get_next_step(self, reservation: Reservation) -> dict[str, Any] | None:
        return services.next_step(reservation)

    def validate_title(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Donnez un titre à l’événement.")
        return value

    def to_representation(self, instance: Reservation) -> dict[str, Any]:
        return strip(dict(super().to_representation(instance)), self.context)


def line_inputs(rows: list[dict[str, Any]]) -> list[services.LineInput]:
    return [
        services.LineInput(
            kind=row["kind"],
            quantity=row["quantity"],
            item=row.get("item"),
            pack=row.get("pack"),
            service=row.get("service"),
            label=row.get("label", "") or "",
            unit_price=row.get("unit_price"),
            period_days=row.get("period_days", 1) or 1,
            deposit=row.get("deposit"),
        )
        for row in rows
    ]


class MoveSerializer(serializers.Serializer[Any]):
    days = serializers.IntegerField(min_value=-366, max_value=366)


class StatusSerializer(serializers.Serializer[Any]):
    status = serializers.ChoiceField(choices=Reservation.Status.choices)


class CheckoutSerializer(serializers.Serializer[Any]):
    quantities = serializers.DictField(
        child=serializers.IntegerField(min_value=0), required=False, default=dict
    )


class ReturnLineSerializer(serializers.Serializer[Any]):
    returned = serializers.IntegerField(min_value=0)
    damaged = serializers.IntegerField(min_value=0, default=0)
    missing = serializers.IntegerField(min_value=0, default=0)


class ReturnSerializer(serializers.Serializer[Any]):
    lines = serializers.DictField(child=ReturnLineSerializer(), required=False, default=dict)


class CancelSerializer(serializers.Serializer[Any]):
    reason = serializers.CharField()


class PaymentInputSerializer(serializers.Serializer[Any]):
    amount = serializers.IntegerField(min_value=1)
    method = serializers.ChoiceField(choices=ReservationPayment.Method.choices)
    paid_at = serializers.DateField()
    reference = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")
    kind = serializers.ChoiceField(
        choices=[("payment", "Paiement"), ("security", "Caution")], default="payment"
    )


class SecuritySerializer(serializers.Serializer[Any]):
    retained = serializers.IntegerField(min_value=0, default=0)
    method = serializers.ChoiceField(choices=ReservationPayment.Method.choices)
    reason = serializers.CharField(required=False, allow_blank=True, default="")
