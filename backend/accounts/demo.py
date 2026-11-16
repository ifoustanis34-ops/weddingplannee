"""Presentation mode (feedback 16/11/2026): the app plays the journeys of a demo agency by itself
and shows each role's point of view (owner, planner, storekeeper, team lead, staff).

Switching role signs the browser in as the member of that role, without a password, so it only
exists where it is harmless: `DEMO_MODE` on (off by default, never on a real deployment without
intent) and the current space listed in `DEMO_ORGANIZATIONS` (fictitious agencies only). The
signed-in person must already belong to that space. Every switch is audited.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core import audit
from core.exceptions import BusinessError
from core.permissions import IsTenantMember

from . import tokens
from .models import Membership

ROLES = [r for r in Membership.Role.values if r != Membership.Role.OWNER] + [Membership.Role.OWNER]


def demo_space(request: Request) -> bool:
    organization = getattr(request, "organization", None)
    return bool(
        settings.DEMO_MODE
        and organization is not None
        and organization.slug in settings.DEMO_ORGANIZATIONS
    )


class DemoConfigView(APIView):
    """Whether the presentation mode is open here, and which roles it can show."""

    permission_classes = [IsTenantMember]
    open_to_field_roles = True

    def get(self, request: Request) -> Response:
        if not demo_space(request):
            return Response({"enabled": False, "roles": []})
        present = set(
            Membership.objects.filter(
                organization=request.organization,  # type: ignore[attr-defined]
                is_active=True,
                user__is_active=True,
            ).values_list("role", flat=True)
        )
        return Response({"enabled": True, "roles": [r for r in ROLES if r in present]})


class SwitchSerializer(serializers.Serializer[Any]):
    role = serializers.ChoiceField(choices=Membership.Role.choices)


class DemoSwitchView(APIView):
    """Sign in as the demo member who holds this role in the current (demo) space."""

    permission_classes = [IsTenantMember]
    open_to_field_roles = True

    @extend_schema(request=SwitchSerializer)
    def post(self, request: Request) -> Response:
        from .views import session_payload

        if not demo_space(request):
            raise BusinessError(
                "demo_disabled",
                "Le mode présentation n’est ouvert que sur une agence de démonstration.",
                status_code=403,
            )
        serializer = SwitchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data["role"]
        membership = (
            Membership.objects.select_related("user")
            .filter(
                organization=request.organization,  # type: ignore[attr-defined]
                role=role,
                is_active=True,
                user__is_active=True,
            )
            .order_by("joined_at", "pk")
            .first()
        )
        if membership is None:
            raise BusinessError(
                "not_found", "Aucun compte de démonstration pour ce rôle.", status_code=404
            )
        audit.record(
            "demo.role_switched",
            membership,
            request=request,
            changes={"from": str(request.user.pk), "to": str(membership.user_id), "role": role},
        )
        response = Response(session_payload(membership.user))
        tokens.set_auth_cookies(response, tokens.issue_tokens(membership.user))
        return response
