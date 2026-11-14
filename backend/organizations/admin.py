from __future__ import annotations

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils import timezone

from .models import Organization, SubscriptionPlan
from .services import invalidate_organization


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Prices and limits of the offers are edited here, never in code (CLAUDE.md §7.9)."""

    list_display = ["name", "code", "monthly_price", "max_users", "position", "is_active"]
    list_editable = ["monthly_price", "max_users", "position", "is_active"]


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Every agency. Suspending or giving lifetime access is also done from /plateforme."""

    list_display = [
        "name",
        "slug",
        "city",
        "plan",
        "trial_ends_at",
        "lifetime_access",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active", "lifetime_access", "plan", "country", "weddings_enabled"]
    search_fields = ["name", "slug", "city"]
    readonly_fields = ["id", "created_at", "updated_at", "lifetime_granted_at", "suspended_at"]
    actions = ["grant_lifetime", "revoke_lifetime", "suspend", "reactivate"]
    fieldsets = (
        (None, {"fields": ("id", "name", "slug", "city", "country", "currency", "timezone")}),
        (
            "Abonnement",
            {"fields": ("plan", "trial_ends_at", "lifetime_access", "lifetime_granted_at")},
        ),
        ("Statut", {"fields": ("is_active", "suspended_at", "suspension_reason", "admin_note")}),
        ("Modules", {"fields": ("weddings_enabled", "alert_digest", "deposit_kept_on_cancel")}),
        ("Dates", {"fields": ("created_at", "updated_at")}),
    )

    def has_delete_permission(self, request: HttpRequest, obj: object = None) -> bool:
        # The agency's data lives under RLS: deleting it from here would fail half way.
        # Suspend it instead.
        return False

    def save_model(
        self, request: HttpRequest, obj: Organization, form: object, change: bool
    ) -> None:
        now = timezone.now()
        if obj.lifetime_access and obj.lifetime_granted_at is None:
            obj.lifetime_granted_at = now
        if not obj.lifetime_access:
            obj.lifetime_granted_at = None
        if not obj.is_active and obj.suspended_at is None:
            obj.suspended_at = now
        if obj.is_active:
            obj.suspended_at, obj.suspension_reason = None, ""
        super().save_model(request, obj, form, change)
        invalidate_organization(obj)

    def _bulk(
        self, request: HttpRequest, queryset: QuerySet[Organization], **fields: object
    ) -> None:
        count = queryset.update(**fields)
        for organization in queryset:
            invalidate_organization(organization)
        self.message_user(request, f"{count} agence(s) mise(s) à jour.", messages.SUCCESS)

    @admin.action(description="Donner l’accès à vie")
    def grant_lifetime(self, request: HttpRequest, queryset: QuerySet[Organization]) -> None:
        self._bulk(request, queryset, lifetime_access=True, lifetime_granted_at=timezone.now())

    @admin.action(description="Retirer l’accès à vie")
    def revoke_lifetime(self, request: HttpRequest, queryset: QuerySet[Organization]) -> None:
        self._bulk(request, queryset, lifetime_access=False, lifetime_granted_at=None)

    @admin.action(description="Suspendre (plus personne n’entre)")
    def suspend(self, request: HttpRequest, queryset: QuerySet[Organization]) -> None:
        self._bulk(request, queryset, is_active=False, suspended_at=timezone.now())

    @admin.action(description="Réactiver")
    def reactivate(self, request: HttpRequest, queryset: QuerySet[Organization]) -> None:
        self._bulk(request, queryset, is_active=True, suspended_at=None, suspension_reason="")
