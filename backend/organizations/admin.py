from django.contrib import admin

from .models import SubscriptionPlan


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Prices and limits of the offers are edited here, never in code (CLAUDE.md §7.9)."""

    list_display = ["name", "code", "monthly_price", "max_users", "position", "is_active"]
    list_editable = ["monthly_price", "max_users", "position", "is_active"]
