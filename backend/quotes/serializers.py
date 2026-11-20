from __future__ import annotations

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from catalog.models import ServiceItem, Unit
from core.fields import TenantPrimaryKeyRelatedField
from crm.models import Client
from crm.serializers import ClientSummarySerializer
from documents import icons
from documents.palettes import PALETTES
from documents.quote_document import TEMPLATES
from documents.services import logo_url

from .models import Quote, QuoteLine, QuotePartner
from .services import public_url


class QuoteLineSerializer(serializers.ModelSerializer[QuoteLine]):
    service_item = TenantPrimaryKeyRelatedField(ServiceItem, allow_null=True, required=False)
    unit = serializers.ChoiceField(choices=Unit.choices, default=Unit.FLAT)
    unit_label = serializers.CharField(source="get_unit_display", read_only=True)
    unit_price = serializers.IntegerField(min_value=0)
    quantity = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.01"), coerce_to_string=False
    )

    class Meta:
        model = QuoteLine
        fields = [
            "id",
            "service_item",
            "label",
            "description",
            "unit",
            "unit_label",
            "unit_price",
            "quantity",
            "amount",
            "icon",
        ]
        read_only_fields = ["id", "amount"]

    def validate_icon(self, value: str) -> str:
        if value and value not in icons.PATHS:
            raise serializers.ValidationError("Icône inconnue.")
        return value


class QuotePartnerSerializer(serializers.ModelSerializer[QuotePartner]):
    class Meta:
        model = QuotePartner
        fields = ["id", "name", "activity", "signatory", "signatory_role"]
        read_only_fields = ["id"]


class QuoteSerializer(serializers.ModelSerializer[Quote]):
    lines = QuoteLineSerializer(many=True)
    partners = QuotePartnerSerializer(many=True, required=False)
    client = TenantPrimaryKeyRelatedField(
        Client, filters={"is_deleted": False}, allow_null=True, required=False
    )
    client_detail = ClientSummarySerializer(source="client", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    discount_pct = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
        coerce_to_string=False,
        required=False,
    )
    deposit_pct = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
        coerce_to_string=False,
        required=False,
    )
    public_url = serializers.SerializerMethodField()
    contract = serializers.SerializerMethodField()

    class Meta:
        model = Quote
        fields = [
            "id",
            "number",
            "client",
            "client_detail",
            "status",
            "status_label",
            "issue_date",
            "valid_until",
            "wedding_date",
            "guest_count",
            "discount_pct",
            "deposit_pct",
            "payment_terms",
            "notes",
            "subtotal",
            "discount_amount",
            "total",
            "deposit_amount",
            "sent_at",
            "accepted_at",
            "refused_at",
            "refusal_reason",
            "is_template",
            "template_name",
            "public_url",
            "contract",
            "lines",
            "design",
            "palette",
            "tagline",
            "event_type",
            "venue",
            "partners",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "number",
            "status",
            "subtotal",
            "discount_amount",
            "total",
            "deposit_amount",
            "sent_at",
            "accepted_at",
            "refused_at",
            "refusal_reason",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "issue_date": {"required": False},
            "valid_until": {"required": False},
        }

    def get_public_url(self, quote: Quote) -> str | None:
        return None if quote.is_template else public_url(quote)

    def get_contract(self, quote: Quote) -> dict[str, str] | None:
        contract = getattr(quote, "contract", None)
        return {"id": str(contract.pk), "number": contract.number} if contract else None

    def validate_design(self, value: str) -> str:
        if value and value not in TEMPLATES:
            raise serializers.ValidationError("Modèle inconnu.")
        return value

    def validate_palette(self, value: str) -> str:
        if value and value not in PALETTES:
            raise serializers.ValidationError("Palette inconnue.")
        return value

    def validate_partners(self, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(value) > 2:
            raise serializers.ValidationError("Deux partenaires au maximum.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        issue = attrs.get("issue_date") or (self.instance.issue_date if self.instance else None)
        valid = attrs.get("valid_until")
        if issue and valid and valid < issue:
            raise serializers.ValidationError(
                {"valid_until": ["La validité doit suivre la date d’émission."]}
            )
        return attrs


class QuoteListSerializer(serializers.ModelSerializer[Quote]):
    client_name = serializers.CharField(source="client.name", read_only=True, default=None)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    # Annotated by the list view (Exists subquery, no N+1).
    has_contract = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = Quote
        fields = [
            "id",
            "number",
            "has_contract",
            "client",
            "client_name",
            "status",
            "status_label",
            "issue_date",
            "valid_until",
            "wedding_date",
            "total",
            "sent_at",
            "is_template",
            "template_name",
            "updated_at",
        ]


class DuplicateSerializer(serializers.Serializer[Any]):
    as_template = serializers.BooleanField(default=False)
    client = TenantPrimaryKeyRelatedField(
        Client, filters={"is_deleted": False}, required=False, allow_null=True
    )


class SendSerializer(serializers.Serializer[Any]):
    channel = serializers.ChoiceField(choices=["email", "whatsapp"], default="email")


class RefuseSerializer(serializers.Serializer[Any]):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class PublicLineSerializer(serializers.ModelSerializer[QuoteLine]):
    unit_label = serializers.CharField(source="get_unit_display")
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=False)

    class Meta:
        model = QuoteLine
        fields = ["label", "description", "unit", "unit_label", "unit_price", "quantity", "amount"]


class PublicQuoteSerializer(serializers.ModelSerializer[Quote]):
    """What the client sees through the public link: no internal ids, notes or history."""

    organization = serializers.SerializerMethodField()
    client_name = serializers.CharField(source="client.name")
    status_label = serializers.CharField(source="get_status_display")
    lines = PublicLineSerializer(many=True)
    discount_pct = serializers.DecimalField(max_digits=5, decimal_places=2, coerce_to_string=False)
    deposit_pct = serializers.DecimalField(max_digits=5, decimal_places=2, coerce_to_string=False)

    class Meta:
        model = Quote
        fields = [
            "number",
            "organization",
            "client_name",
            "status",
            "status_label",
            "issue_date",
            "valid_until",
            "wedding_date",
            "guest_count",
            "discount_pct",
            "deposit_pct",
            "payment_terms",
            "notes",
            "subtotal",
            "discount_amount",
            "total",
            "deposit_amount",
            "accepted_at",
            "refused_at",
            "lines",
        ]

    def get_organization(self, quote: Quote) -> dict[str, Any]:
        org = quote.organization
        return {
            "name": org.name,
            "city": org.city,
            "legal_mentions": org.legal_mentions,
            "logo": logo_url(),
        }
