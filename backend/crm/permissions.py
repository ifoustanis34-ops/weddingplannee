from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import Membership

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView

Role = Membership.Role


class ClientPermission(BasePermission):
    """CLAUDE.md §11: everyone reads; owner, planner, assistant edit; assistant cannot delete."""

    WRITE = frozenset({Role.OWNER, Role.PLANNER, Role.ASSISTANT})
    DELETE = frozenset({Role.OWNER, Role.PLANNER})

    def has_permission(self, request: Request, view: APIView) -> bool:
        membership = getattr(request, "membership", None)
        role = membership.role if membership is not None else None
        if request.method in SAFE_METHODS:
            return True
        if request.method == "DELETE":
            self.message = "Votre rôle ne permet pas de supprimer un client."
            return role in self.DELETE
        self.message = "Votre rôle permet seulement la consultation."
        return role in self.WRITE
