from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest

from .models import PlatformAuditLog


@admin.register(PlatformAuditLog)
class PlatformAuditLogAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Read-only: a trace is never edited."""

    list_display = ["created_at", "action", "target_label", "organization", "actor", "ip"]
    list_filter = ["action"]
    search_fields = ["target_label", "action", "actor__email"]
    list_select_related = ["organization", "actor"]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return False
