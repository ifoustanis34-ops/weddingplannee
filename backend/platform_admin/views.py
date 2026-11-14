"""Platform console API (``/api/v1/platform/…``): Wedivo team only, never tenant-scoped."""

from __future__ import annotations

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Membership, User
from core.audit import client_ip
from core.exceptions import BusinessError
from organizations.models import Organization

from . import services
from .pagination import ConsolePagination
from .permissions import IsPlatformAdmin
from .serializers import (
    AccountCreateSerializer,
    AccountSerializer,
    AccountUpdateSerializer,
    AgencyCreateSerializer,
    AgencyMemberSerializer,
    AgencySerializer,
    AgencyUpdateSerializer,
    JournalSerializer,
    MembershipCreateSerializer,
    MembershipUpdateSerializer,
    PasswordSerializer,
)


class ConsoleView(APIView):
    permission_classes = [IsPlatformAdmin]


class ConsoleListView(ListAPIView):  # type: ignore[type-arg]
    permission_classes = [IsPlatformAdmin]
    pagination_class = ConsolePagination


def _actor(request: Request) -> User:
    return request.user  # type: ignore[return-value]


class OverviewView(ConsoleView):
    @extend_schema(responses={200: dict})
    def get(self, request: Request) -> Response:
        admin_url = settings.DJANGO_ADMIN_URL
        return Response(
            {**services.overview(), "django_admin_url": f"/{admin_url}" if admin_url else None}
        )


class AgencyListView(ConsoleListView):
    serializer_class = AgencySerializer

    def get_queryset(self):  # type: ignore[no-untyped-def]
        params = self.request.query_params
        return services.organizations(params.get("search", ""), params.get("status", ""))

    @extend_schema(request=AgencyCreateSerializer, responses={201: AgencySerializer})
    def post(self, request: Request) -> Response:
        serializer = AgencyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization, owner, created = services.create_organization(
            services.NewAgency(**serializer.validated_data),
            actor=_actor(request),
            ip=client_ip(request),
        )
        return Response(
            {
                "agency": AgencySerializer(services.organization_detail(organization.pk)).data,
                "owner_email": owner.email,
                "created_account": created,
            },
            status=status.HTTP_201_CREATED,
        )


class AgencyDetailView(ConsoleView):
    @extend_schema(responses=AgencySerializer)
    def get(self, request: Request, pk: str) -> Response:
        return Response(AgencySerializer(services.organization_detail(pk)).data)

    @extend_schema(request=AgencyUpdateSerializer, responses=AgencySerializer)
    def patch(self, request: Request, pk: str) -> Response:
        organization = services.organization_detail(pk)
        serializer = AgencyUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_organization(
            organization, serializer.validated_data, actor=_actor(request), ip=client_ip(request)
        )
        return Response(AgencySerializer(services.organization_detail(pk)).data)


class AgencyMembersView(ConsoleView):
    @extend_schema(responses=AgencyMemberSerializer(many=True))
    def get(self, request: Request, pk: str) -> Response:
        organization = services.organization_detail(pk)
        return Response(
            AgencyMemberSerializer(services.organization_members(organization), many=True).data
        )


class AccountListView(ConsoleListView):
    serializer_class = AccountSerializer

    def get_queryset(self):  # type: ignore[no-untyped-def]
        params = self.request.query_params
        return services.users(
            params.get("search", ""), params.get("status", ""), params.get("organization", "")
        )

    @extend_schema(request=AccountCreateSerializer, responses={201: AccountSerializer})
    def post(self, request: Request) -> Response:
        serializer = AccountCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        if data.get("organization_id") and not data.get("role"):
            raise BusinessError("invalid", "Choisissez un rôle.", {"role": ["Champ obligatoire."]})
        user, _ = services.create_user(
            services.NewAccount(**data), actor=_actor(request), ip=client_ip(request)
        )
        return Response(
            AccountSerializer(services.user_detail(user.pk)).data, status=status.HTTP_201_CREATED
        )


class AccountDetailView(ConsoleView):
    @extend_schema(responses=AccountSerializer)
    def get(self, request: Request, pk: str) -> Response:
        return Response(AccountSerializer(services.user_detail(pk)).data)

    @extend_schema(request=AccountUpdateSerializer, responses=AccountSerializer)
    def patch(self, request: Request, pk: str) -> Response:
        user = services.user_detail(pk)
        serializer = AccountUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_user(
            user, serializer.validated_data, actor=_actor(request), ip=client_ip(request)
        )
        return Response(AccountSerializer(services.user_detail(pk)).data)


class AccountPasswordView(ConsoleView):
    @extend_schema(request=PasswordSerializer, responses={204: None})
    def post(self, request: Request, pk: str) -> Response:
        user = services.user_detail(pk)
        serializer = PasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.set_password(
            user,
            serializer.validated_data["password"],
            actor=_actor(request),
            ip=client_ip(request),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountMembershipsView(ConsoleView):
    """Place the account in an agency with a role."""

    @extend_schema(request=MembershipCreateSerializer, responses={201: AccountSerializer})
    def post(self, request: Request, pk: str) -> Response:
        user = services.user_detail(pk)
        serializer = MembershipCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = Organization.objects.filter(
            pk=serializer.validated_data["organization_id"]
        ).first()
        if organization is None:
            raise BusinessError("not_found", "Agence introuvable.", status_code=404)
        services.add_membership(
            organization,
            user,
            serializer.validated_data["role"],
            actor=_actor(request),
            ip=client_ip(request),
        )
        return Response(
            AccountSerializer(services.user_detail(pk)).data, status=status.HTTP_201_CREATED
        )


class MembershipDetailView(ConsoleView):
    @extend_schema(request=MembershipUpdateSerializer, responses=AgencyMemberSerializer)
    def patch(self, request: Request, pk: str) -> Response:
        membership: Membership = services.membership_or_404(pk)
        serializer = MembershipUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_membership(
            membership, serializer.validated_data, actor=_actor(request), ip=client_ip(request)
        )
        return Response(AgencyMemberSerializer(services.membership_or_404(pk)).data)


class JournalView(ConsoleListView):
    serializer_class = JournalSerializer

    def get_queryset(self):  # type: ignore[no-untyped-def]
        params = self.request.query_params
        return services.journal(params.get("organization", ""), params.get("search", ""))
