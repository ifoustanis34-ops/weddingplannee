"""Who does what with the reservations (reservations-stock.md §12)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import Membership

if TYPE_CHECKING:
    from rest_framework.request import Request

Role = Membership.Role
READ = frozenset({Role.OWNER, Role.PLANNER, Role.ASSISTANT, Role.ACCOUNTANT, Role.STOREKEEPER})
# Create, edit, confirm, cancel.
EDIT = frozenset({Role.OWNER, Role.PLANNER})
# Logistics: steps, checkout and return (the storekeeper loads and receives the equipment).
LOGISTICS = frozenset({Role.OWNER, Role.PLANNER, Role.STOREKEEPER})
# Money in: payments and the security deposit.
PAYMENTS = frozenset({Role.OWNER, Role.ACCOUNTANT})


def role_of(request: Request) -> str | None:
    membership = getattr(request, "membership", None)
    return membership.role if membership is not None else None


class ReservationPermission(BasePermission):
    """Reads for READ; writes need the view's `write_roles` (EDIT by default)."""

    def has_permission(self, request: Request, view: Any) -> bool:
        role = role_of(request)
        if request.method in SAFE_METHODS:
            self.message = "Votre rôle n’a pas accès aux réservations."
            return role in READ
        allowed = getattr(view, "write_roles", EDIT)
        self.message = "Votre rôle ne permet pas cette action sur les réservations."
        return role in allowed
