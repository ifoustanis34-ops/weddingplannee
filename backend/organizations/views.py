from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import services as account_services
from accounts.models import Membership
from accounts.views import PublicAPIView
from core import audit
from core.permissions import IsTenantMember, read_any_write_roles, roles_allowed

from . import selectors, services
from .models import SubscriptionPlan
from .serializers import (
    InvitationSerializer,
    MemberCreatedSerializer,
    MemberCreateSerializer,
    MemberPasswordSerializer,
    MemberSerializer,
    MemberUpdateSerializer,
    OrganizationSerializer,
    PlanChangeSerializer,
    SubscriptionPlanSerializer,
)


class OrganizationView(APIView):
    """Settings of the current space. Every member reads; only the owner edits."""

    permission_classes = [IsTenantMember, read_any_write_roles([Membership.Role.OWNER])]
    open_to_field_roles = True  # the shell reads the time zone and the name

    @extend_schema(responses=OrganizationSerializer)
    def get(self, request: Request) -> Response:
        return Response(OrganizationSerializer(request.organization).data)  # type: ignore[attr-defined]

    @extend_schema(request=OrganizationSerializer, responses=OrganizationSerializer)
    def patch(self, request: Request) -> Response:
        organization = request.organization  # type: ignore[attr-defined]
        serializer = OrganizationSerializer(organization, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        changes = services.update_organization(organization, dict(serializer.validated_data))
        if changes:
            audit.record("organization.updated", organization, request=request, changes=changes)
        return Response(OrganizationSerializer(organization).data, status=status.HTTP_200_OK)


class MemberListView(ListAPIView[Membership]):
    open_to_field_roles = True  # names of the team (assignments, planning)
    serializer_class = MemberSerializer
    pagination_class = None

    def get_queryset(self):  # type: ignore[no-untyped-def]
        if getattr(self, "swagger_fake_view", False):  # OpenAPI generation has no tenant
            return Membership.objects.none()
        return selectors.members_of(self.request.organization)  # type: ignore[attr-defined]

    def get_permissions(self) -> list[BasePermission]:
        if self.request.method == "POST":  # creating an account: the owner only
            return [permission() for permission in OWNER_ONLY]
        return list(super().get_permissions())  # type: ignore[arg-type]

    @extend_schema(request=MemberCreateSerializer, responses={201: MemberCreatedSerializer})
    def post(self, request: Request) -> Response:
        """The owner opens an account for a team member (temporary password, changed at first
        sign-in), without waiting for an email (feedback 13/11/2026)."""
        serializer = MemberCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership, created = account_services.create_member(
            request.organization,  # type: ignore[attr-defined]
            account_services.NewMember(**serializer.validated_data),
            created_by=request.user,  # type: ignore[arg-type]
        )
        audit.record(
            "membership.created",
            membership,
            request=request,
            changes={"email": membership.user.email, "role": membership.role, "new": created},
        )
        return Response(
            {"member": MemberSerializer(membership).data, "created_account": created},
            status=status.HTTP_201_CREATED,
        )


class PlanListView(PublicAPIView):
    """Active offers with their monthly price (signup and subscription screens)."""

    @extend_schema(responses=SubscriptionPlanSerializer(many=True))
    def get(self, request: Request) -> Response:
        plans = SubscriptionPlan.objects.filter(is_active=True)
        return Response(SubscriptionPlanSerializer(plans, many=True).data)


OWNER_ONLY: list[type[BasePermission]] = [IsTenantMember, roles_allowed(Membership.Role.OWNER)]


class MemberDetailView(APIView):
    """Change a member's role or deactivate them (owner only, audited)."""

    permission_classes = OWNER_ONLY

    @extend_schema(request=MemberUpdateSerializer, responses=MemberSerializer)
    def patch(self, request: Request, pk: str) -> Response:
        serializer = MemberUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership, changes = account_services.update_member(
            request.organization,  # type: ignore[attr-defined]
            pk,
            role=serializer.validated_data.get("role"),
            is_active=serializer.validated_data.get("is_active"),
        )
        if "role" in changes:
            audit.record("membership.role_changed", membership, request=request, changes=changes)
        elif changes:
            audit.record("membership.access_changed", membership, request=request, changes=changes)
        return Response(MemberSerializer(membership).data)


class MemberPasswordView(APIView):
    """The owner gives a member a new temporary password (owner only, audited)."""

    permission_classes = OWNER_ONLY

    @extend_schema(request=MemberPasswordSerializer, responses={204: None})
    def post(self, request: Request, pk: str) -> Response:
        serializer = MemberPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = account_services.set_member_password(
            request.organization,  # type: ignore[attr-defined]
            pk,
            serializer.validated_data["password"],
        )
        audit.record("membership.password_set", membership, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class InvitationListView(APIView):
    """Pending invitations; the owner invites a member by email with a role."""

    permission_classes = OWNER_ONLY

    @extend_schema(responses=InvitationSerializer(many=True))
    def get(self, request: Request) -> Response:
        invitations = account_services.pending_invitations(request.organization)  # type: ignore[attr-defined]
        return Response(InvitationSerializer(invitations, many=True).data)

    @extend_schema(request=InvitationSerializer, responses={201: InvitationSerializer})
    def post(self, request: Request) -> Response:
        serializer = InvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation = account_services.invite_member(
            request.organization,  # type: ignore[attr-defined]
            email=serializer.validated_data["email"],
            role=serializer.validated_data["role"],
            invited_by=request.user,  # type: ignore[arg-type]
        )
        audit.record(
            "membership.invited",
            invitation,
            request=request,
            changes={"email": invitation.email, "role": invitation.role},
        )
        return Response(InvitationSerializer(invitation).data, status=status.HTTP_201_CREATED)


class InvitationDetailView(APIView):
    permission_classes = OWNER_ONLY

    @extend_schema(responses={204: None})
    def delete(self, request: Request, pk: str) -> Response:
        invitation = account_services.cancel_invitation(request.organization, pk)  # type: ignore[attr-defined]
        audit.record("membership.invitation_cancelled", invitation, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PlanChangeView(APIView):
    """Choose the offer (during the trial: no payment integration yet)."""

    permission_classes = OWNER_ONLY

    @extend_schema(request=PlanChangeSerializer, responses=OrganizationSerializer)
    def post(self, request: Request) -> Response:
        serializer = PlanChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = request.organization  # type: ignore[attr-defined]
        changes = services.change_plan(organization, serializer.validated_data["plan"])
        if changes:
            audit.record(
                "organization.plan_changed", organization, request=request, changes=changes
            )
        return Response(OrganizationSerializer(organization).data)
