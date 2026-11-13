from __future__ import annotations

from typing import Any

from rest_framework import serializers

from organizations.models import Organization

from .models import Membership, User


class SignupSerializer(serializers.Serializer[Any]):
    # Step 1: company
    company_name = serializers.CharField(max_length=120)
    city = serializers.CharField(max_length=80)
    country = serializers.RegexField(
        r"^[A-Za-z]{2}$", error_messages={"invalid": "Code pays sur 2 lettres, ex. CI."}
    )
    weddings_per_year = serializers.IntegerField(
        min_value=0, max_value=1000, required=False, allow_null=True, default=None
    )
    # Step 2: account
    full_name = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=32, allow_blank=True, required=False, default="")
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)
    # Step 3: space
    slug = serializers.CharField(max_length=32)
    plan = serializers.ChoiceField(choices=Organization.Plan.choices, default=Organization.Plan.PRO)
    # « J’organise des mariages » (feedback 13/11/2026): turns the « Mariages » module on.
    weddings_enabled = serializers.BooleanField(required=False, default=False)


class LoginSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False)


class TokenSerializer(serializers.Serializer[Any]):
    token = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer[Any]):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class SlugQuerySerializer(serializers.Serializer[Any]):
    slug = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField(required=False, allow_blank=True)


class SlugAvailabilitySerializer(serializers.Serializer[Any]):
    slug = serializers.CharField()
    available = serializers.BooleanField()
    reason = serializers.CharField(allow_null=True)


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["id", "email", "full_name", "phone", "is_verified", "must_change_password"]
        read_only_fields = fields


class MembershipSummarySerializer(serializers.ModelSerializer[Membership]):
    organization_id = serializers.UUIDField(source="organization.id")
    slug = serializers.CharField(source="organization.slug")
    name = serializers.CharField(source="organization.name")
    role_label = serializers.CharField(source="get_role_display")
    weddings_enabled = serializers.BooleanField(source="organization.weddings_enabled")

    class Meta:
        model = Membership
        fields = ["organization_id", "slug", "name", "role", "role_label", "weddings_enabled"]
        read_only_fields = fields


class SessionSerializer(serializers.Serializer[Any]):
    user = UserSerializer()
    organizations = MembershipSummarySerializer(many=True)


class InvitationPreviewSerializer(serializers.Serializer[Any]):
    organization_name = serializers.CharField()
    organization_slug = serializers.CharField()
    email = serializers.EmailField()
    role_label = serializers.CharField()
    invited_by_name = serializers.CharField(allow_null=True)
    has_account = serializers.BooleanField()


class AcceptInvitationSerializer(serializers.Serializer[Any]):
    full_name = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class ProfileSerializer(serializers.Serializer[Any]):
    full_name = serializers.CharField(max_length=120, required=False)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)


class PasswordChangeSerializer(serializers.Serializer[Any]):
    current_password = serializers.CharField(max_length=128, trim_whitespace=False)
    new_password = serializers.CharField(max_length=128, trim_whitespace=False)
