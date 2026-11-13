from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .visibility import FULL, can_see_balances, can_see_margins

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView


def role_of(request: Request) -> str | None:
    membership = getattr(request, "membership", None)
    return membership.role if membership is not None else None


class FinancePermission(BasePermission):
    """CLAUDE.md §11 — Paiements, marges, exports: owner and accountant; planner reads balances;
    assistant has no access. Views flagged `margins_only` (expenses, exports) exclude the planner.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        role = role_of(request)
        if getattr(view, "margins_only", False):
            self.message = (
                "Les marges et les exports sont réservés au propriétaire et au comptable."
            )
            return can_see_margins(role)
        if request.method in SAFE_METHODS:
            self.message = "Votre rôle n’a pas accès aux finances."
            return can_see_balances(role)
        self.message = "Seuls le propriétaire et le comptable enregistrent les paiements."
        return role in FULL
