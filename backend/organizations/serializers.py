from __future__ import annotations

import zoneinfo
from typing import Any

from rest_framework import serializers

from accounts.models import Membership, TeamInvitation

from .models import Organization, SubscriptionPlan


class OrganizationSerializer(serializers.ModelSerializer[Organization]):
    # Checked by ``services.update_organization`` (same rules as at sign-up).
    slug = serializers.CharField(max_length=32, required=False)
    # The logo is managed in Settings › Identité des documents (documents.OrganizationBranding).
    logo = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "id",
            "slug",
            "name",
            "logo",
            "country",
            "city",
            "currency",
            "timezone",
            "weddings_per_year",
            "plan",
            "trial_ends_at",
            "lifetime_access",
            "quote_prefix",
            "quote_validity_days",
            "legal_mentions",
            "alert_digest",
            "deposit_kept_on_cancel",
            "weddings_enabled",
        ]
        read_only_fields = ["id", "plan", "trial_ends_at", "lifetime_access"]

    def get_logo(self, organization: Organization) -> str | None:
        from documents.services import logo_url

        return logo_url()

    def validate_timezone(self, value: str) -> str:
        if value not in zoneinfo.available_timezones():
            raise serializers.ValidationError("Fuseau horaire inconnu.")
        return value

    def validate_country(self, value: str) -> str:
        if len(value) != 2 or not value.isalpha():
            raise serializers.ValidationError("Code pays sur 2 lettres, ex. CI.")
        return value.upper()

    def validate_quote_prefix(self, value: str) -> str:
        if not value.isalnum():
            raise serializers.ValidationError("Lettres et chiffres uniquement.")
        return value.upper()


class MemberSerializer(serializers.ModelSerializer[Membership]):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    role_label = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = Membership
        fields = [
            "id",
            "user_id",
            "full_name",
            "email",
            "phone",
            "role",
            "role_label",
            "is_active",
            "invited_at",
            "joined_at",
        ]
        read_only_fields = fields


class SubscriptionPlanSerializer(serializers.ModelSerializer[SubscriptionPlan]):
    class Meta:
        model = SubscriptionPlan
        fields = ["code", "name", "description", "monthly_price", "max_users", "features"]


class InvitationSerializer(serializers.ModelSerializer[TeamInvitation]):
    role_label = serializers.CharField(source="get_role_display", read_only=True)
    invited_by_name = serializers.CharField(
        source="invited_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = TeamInvitation
        fields = [
            "id",
            "email",
            "role",
            "role_label",
            "invited_by_name",
            "created_at",
            "expires_at",
        ]
        read_only_fields = ["id", "created_at", "expires_at"]


class MemberCreateSerializer(serializers.Serializer[Any]):
    full_name = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")
    role = serializers.ChoiceField(choices=Membership.Role.choices)
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class MemberCreatedSerializer(serializers.Serializer[Any]):
    member = MemberSerializer()
    created_account = serializers.BooleanField()


class MemberPasswordSerializer(serializers.Serializer[Any]):
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class MemberUpdateSerializer(serializers.Serializer[Any]):
    role = serializers.ChoiceField(choices=Membership.Role.choices, required=False)
    is_active = serializers.BooleanField(required=False)


class PlanChangeSerializer(serializers.Serializer[Any]):
    plan = serializers.ChoiceField(choices=Organization.Plan.choices)
