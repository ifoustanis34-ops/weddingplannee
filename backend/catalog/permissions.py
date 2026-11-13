from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import Membership

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView


class CatalogPermission(BasePermission):
    """Everyone reads prices (quotes); owner and planner maintain the catalog."""

    message = "Seuls le propriétaire et les wedding planners modifient le catalogue."
    WRITE = frozenset({Membership.Role.OWNER, Membership.Role.PLANNER})

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method in SAFE_METHODS:
            return True
        membership = getattr(request, "membership", None)
        return membership is not None and membership.role in self.WRITE
