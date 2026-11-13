from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import Membership

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView

Role = Membership.Role


class QuotePermission(BasePermission):
    """CLAUDE.md §11: everyone reads; owner, planner, assistant edit and send; delete drafts:
    owner and planner. Converting into a contract (money) is reserved to owner and planner."""

    WRITE = frozenset({Role.OWNER, Role.PLANNER, Role.ASSISTANT})
    MANAGE = frozenset({Role.OWNER, Role.PLANNER})

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method in SAFE_METHODS:
            return True
        membership = getattr(request, "membership", None)
        role = membership.role if membership is not None else None
        if request.method == "DELETE" or getattr(view, "manage_only", False):
            self.message = "Votre rôle ne permet pas cette action sur les devis."
            return role in self.MANAGE
        self.message = "Votre rôle permet seulement la consultation."
        return role in self.WRITE
