"""Role-based permissions (CLAUDE.md §11). The frontend only hides; the server decides."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import Membership

if TYPE_CHECKING:
    # Type-only: this module is loaded by DRF settings while rest_framework.views initializes.
    from rest_framework.request import Request
    from rest_framework.views import APIView


# Storekeeper, team lead and staff (reservations-stock.md §12) only reach the views that say so
# (``open_to_field_roles = True``): their own modules come with stock (S3) and staff (S7).
FIELD_ROLES = frozenset(
    {Membership.Role.STOREKEEPER, Membership.Role.TEAM_LEAD, Membership.Role.STAFF}
)


class IsTenantMember(BasePermission):
    """Default permission: authenticated user with an active membership in the request org.

    Attaches ``request.membership`` for role checks further down.
    """

    message = "Vous n’avez pas accès à cet espace."
    code = "not_a_member"

    def has_permission(self, request: Request, view: APIView) -> bool:
        organization = getattr(request, "organization", None)
        if organization is None or not request.user.is_authenticated:
            return False
        membership = Membership.objects.filter(
            user=request.user, organization=organization, is_active=True
        ).first()
        request.membership = membership  # type: ignore[attr-defined]
        if membership is None:
            return False
        if membership.role in FIELD_ROLES and not getattr(view, "open_to_field_roles", False):
            self.message = "Votre rôle n’a pas accès à ce module."
            return False
        return True


def _role(request: Request) -> str | None:
    membership = getattr(request, "membership", None)
    return membership.role if membership is not None else None


def roles_allowed(*roles: str) -> type[BasePermission]:
    """Members whose role is in ``roles`` (on top of IsTenantMember)."""
    allowed = frozenset(roles)

    class RolePermission(BasePermission):
        message = "Votre rôle ne permet pas cette action."
        code = "role_forbidden"

        def has_permission(self, request: Request, view: APIView) -> bool:
            return _role(request) in allowed

    RolePermission.__name__ = f"RolesAllowed_{'_'.join(sorted(allowed))}"
    return RolePermission


def read_any_write_roles(write_roles: Iterable[str]) -> type[BasePermission]:
    """Every member can read; only ``write_roles`` can create, update or delete."""
    allowed = frozenset(write_roles)

    class ReadAnyWriteRoles(BasePermission):
        message = "Votre rôle permet seulement la consultation."
        code = "role_read_only"

        def has_permission(self, request: Request, view: APIView) -> bool:
            return request.method in SAFE_METHODS or _role(request) in allowed

    ReadAnyWriteRoles.__name__ = f"ReadAnyWrite_{'_'.join(sorted(allowed))}"
    return ReadAnyWriteRoles


IsOwner = roles_allowed(Membership.Role.OWNER)


class WeddingsEnabled(BasePermission):
    """The « Mariages » module (feedback 13/11/2026) is turned on for the current space."""

    message = "Le module Mariages n’est pas activé pour cette entreprise (Paramètres › Entreprise)."

    def has_permission(self, request: Any, view: Any) -> bool:
        organization = getattr(request, "organization", None)
        return bool(organization is not None and organization.weddings_enabled)
