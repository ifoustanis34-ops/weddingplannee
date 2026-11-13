"""Who does what with the stock (reservations-stock.md §12)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import Membership
from finance.visibility import can_see_margins

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView

Role = Membership.Role
# Owner and storekeeper run the stock; planner, assistant and accountant consult it (the planner
# books equipment, the accountant values it). Team leads see their missions' equipment (S7).
READ = frozenset({Role.OWNER, Role.PLANNER, Role.ASSISTANT, Role.ACCOUNTANT, Role.STOREKEEPER})
WRITE = frozenset({Role.OWNER, Role.STOREKEEPER})


def role_of(request: Request) -> str | None:
    membership = getattr(request, "membership", None)
    return membership.role if membership is not None else None


class StockPermission(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        role = role_of(request)
        if request.method in SAFE_METHODS:
            self.message = "Votre rôle n’a pas accès au stock."
            return role in READ
        self.message = "Seuls le propriétaire et le magasinier modifient le stock."
        return role in WRITE


def can_see_prices(role: str | None) -> bool:
    """Rental and sale prices, deposits: never for the storekeeper (§12: « aucun montant »)."""
    return role in READ and role != Role.STOREKEEPER


def can_see_costs(role: str | None) -> bool:
    """Purchase costs, stock value, revenue: owner and accountant only."""
    return can_see_margins(role)
