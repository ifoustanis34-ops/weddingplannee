from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission


class IsPlatformAdmin(BasePermission):
    """Wedivo team only (``is_staff``, CLAUDE.md « Super-admin »), whatever the space.

    Replaces ``IsTenantMember`` on the console views: they never depend on an organization.
    """

    message = "Cette console est réservée à l’équipe Wedivo."
    code = "platform_admin_only"

    def has_permission(self, request: Any, view: Any) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and user.is_staff)
