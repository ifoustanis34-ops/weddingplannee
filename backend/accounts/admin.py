from __future__ import annotations

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import Membership, TeamInvitation, User


class MembershipInline(admin.TabularInline):  # type: ignore[type-arg]
    model = Membership
    fk_name = "user"
    extra = 0
    fields = ["organization", "role", "is_active", "joined_at"]
    readonly_fields = ["joined_at"]
    autocomplete_fields = ["organization"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):  # type: ignore[type-arg]
    """Every Wedivo account (« Super-admin » = Django admin, CLAUDE.md). The platform console
    (/plateforme) does the same with the Wedivo look; both write the same tables."""

    ordering = ["-date_joined"]
    list_display = [
        "email",
        "full_name",
        "phone",
        "is_active",
        "is_staff",
        "must_change_password",
        "last_login",
        "date_joined",
    ]
    list_filter = ["is_active", "is_staff", "is_superuser", "is_verified", "must_change_password"]
    search_fields = ["email", "full_name", "phone"]
    readonly_fields = ["last_login", "date_joined"]
    inlines = [MembershipInline]
    actions = ["deactivate", "reactivate"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Identité", {"fields": ("full_name", "phone", "is_verified", "must_change_password")}),
        (
            "Accès",
            {
                "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
                "description": "« Équipe Wedivo » (is_staff) ouvre la console plateforme.",
            },
        ),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "phone", "password1", "password2"),
            },
        ),
    )

    def has_delete_permission(self, request: HttpRequest, obj: object = None) -> bool:
        # An account is referenced by the agencies' data (RLS): deactivate it instead.
        return False

    @admin.action(description="Désactiver les comptes sélectionnés")
    def deactivate(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        count = queryset.exclude(pk=str(request.user.pk)).update(is_active=False)
        self.message_user(request, f"{count} compte(s) désactivé(s).", messages.SUCCESS)

    @admin.action(description="Réactiver les comptes sélectionnés")
    def reactivate(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} compte(s) réactivé(s).", messages.SUCCESS)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["user", "organization", "role", "is_active", "joined_at"]
    list_filter = ["role", "is_active"]
    search_fields = ["user__email", "user__full_name", "organization__name", "organization__slug"]
    autocomplete_fields = ["user", "organization"]
    list_select_related = ["user", "organization"]


@admin.register(TeamInvitation)
class TeamInvitationAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ["email", "organization", "role", "created_at", "expires_at", "accepted_at"]
    list_filter = ["role"]
    search_fields = ["email", "organization__name"]
    readonly_fields = ["token_hash", "created_at"]
    list_select_related = ["organization"]
