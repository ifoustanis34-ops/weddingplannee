from __future__ import annotations

from typing import Any

from rest_framework import serializers

from accounts.models import Membership, User
from organizations.models import Organization

from .models import PlatformAuditLog


class AgencySerializer(serializers.ModelSerializer[Organization]):
    plan_label = serializers.CharField(source="get_plan_display", read_only=True)
    members_count = serializers.IntegerField(read_only=True)
    owner_name = serializers.CharField(read_only=True, allow_null=True)
    owner_email = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "city",
            "country",
            "currency",
            "plan",
            "plan_label",
            "trial_ends_at",
            "lifetime_access",
            "lifetime_granted_at",
            "is_active",
            "suspended_at",
            "suspension_reason",
            "weddings_enabled",
            "admin_note",
            "members_count",
            "owner_name",
            "owner_email",
            "created_at",
        ]
        read_only_fields = fields


class AgencyCreateSerializer(serializers.Serializer[Any]):
    name = serializers.CharField(max_length=120)
    slug = serializers.CharField(max_length=32)
    city = serializers.CharField(max_length=80)
    country = serializers.CharField(max_length=2)
    plan = serializers.ChoiceField(choices=Organization.Plan.choices, default="pro")
    owner_full_name = serializers.CharField(max_length=120)
    owner_email = serializers.EmailField()
    owner_phone = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")
    owner_password = serializers.CharField(max_length=128, trim_whitespace=False)
    lifetime_access = serializers.BooleanField(default=False)
    weddings_enabled = serializers.BooleanField(default=False)


class AgencyUpdateSerializer(serializers.Serializer[Any]):
    name = serializers.CharField(max_length=120, required=False)
    city = serializers.CharField(max_length=80, required=False)
    country = serializers.CharField(min_length=2, max_length=2, required=False)
    plan = serializers.ChoiceField(choices=Organization.Plan.choices, required=False)
    trial_ends_at = serializers.DateTimeField(required=False, allow_null=True)
    weddings_enabled = serializers.BooleanField(required=False)
    admin_note = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    lifetime_access = serializers.BooleanField(required=False)
    is_active = serializers.BooleanField(required=False)
    suspension_reason = serializers.CharField(required=False, allow_blank=True, max_length=240)


class AgencyMemberSerializer(serializers.ModelSerializer[Membership]):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    user_is_active = serializers.BooleanField(source="user.is_active", read_only=True)
    last_login = serializers.DateTimeField(source="user.last_login", read_only=True)
    role_label = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = Membership
        fields = [
            "id",
            "user_id",
            "full_name",
            "email",
            "phone",
            "user_is_active",
            "last_login",
            "role",
            "role_label",
            "is_active",
            "joined_at",
        ]
        read_only_fields = fields


class UserMembershipSerializer(serializers.ModelSerializer[Membership]):
    organization_id = serializers.UUIDField(source="organization.id", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    organization_slug = serializers.CharField(source="organization.slug", read_only=True)
    organization_is_active = serializers.BooleanField(
        source="organization.is_active", read_only=True
    )
    role_label = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = Membership
        fields = [
            "id",
            "organization_id",
            "organization_name",
            "organization_slug",
            "organization_is_active",
            "role",
            "role_label",
            "is_active",
        ]
        read_only_fields = fields


class AccountSerializer(serializers.ModelSerializer[User]):
    is_platform_admin = serializers.BooleanField(source="is_staff", read_only=True)
    agencies_count = serializers.IntegerField(read_only=True)
    memberships = UserMembershipSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "phone",
            "is_active",
            "is_verified",
            "is_platform_admin",
            "must_change_password",
            "date_joined",
            "last_login",
            "agencies_count",
            "memberships",
        ]
        read_only_fields = fields


class AccountCreateSerializer(serializers.Serializer[Any]):
    full_name = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")
    password = serializers.CharField(max_length=128, trim_whitespace=False)
    organization_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    role = serializers.ChoiceField(
        choices=Membership.Role.choices, required=False, allow_blank=True, default=""
    )
    is_platform_admin = serializers.BooleanField(default=False)


class AccountUpdateSerializer(serializers.Serializer[Any]):
    full_name = serializers.CharField(max_length=120, required=False)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    is_platform_admin = serializers.BooleanField(required=False)


class PasswordSerializer(serializers.Serializer[Any]):
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class MembershipCreateSerializer(serializers.Serializer[Any]):
    organization_id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=Membership.Role.choices)


class MembershipUpdateSerializer(serializers.Serializer[Any]):
    role = serializers.ChoiceField(choices=Membership.Role.choices, required=False)
    is_active = serializers.BooleanField(required=False)


class JournalSerializer(serializers.ModelSerializer[PlatformAuditLog]):
    actor_name = serializers.SerializerMethodField()
    organization_name = serializers.CharField(
        source="organization.name", read_only=True, allow_null=True
    )

    class Meta:
        model = PlatformAuditLog
        fields = [
            "id",
            "action",
            "target_type",
            "target_id",
            "target_label",
            "organization_id",
            "organization_name",
            "changes",
            "actor_name",
            "created_at",
        ]
        read_only_fields = fields

    def get_actor_name(self, entry: PlatformAuditLog) -> str | None:
        return entry.actor.full_name or entry.actor.email if entry.actor else None
