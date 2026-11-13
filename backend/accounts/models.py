from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, ClassVar

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra: Any) -> User:
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra: Any) -> User:
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email: str, password: str | None = None, **extra: Any) -> User:
        extra.update(is_staff=True, is_superuser=True, is_verified=True)
        return self._create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """Platform user, identified by email. Can belong to several organizations."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=32, blank=True)
    is_verified = models.BooleanField(default=False)
    # Set when the owner created the account with a temporary password (feedback 13/11/2026):
    # the person chooses their own at first sign-in.
    must_change_password = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects: ClassVar[UserManager] = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    def __str__(self) -> str:
        return self.email

    @property
    def first_name(self) -> str:
        return self.full_name.split(" ")[0] if self.full_name else ""


class Membership(models.Model):
    """Link between a user and an organization, carrying the role.

    Not a TenantModel: it is the access-control table itself, read before a tenant is active
    (login, space switcher). Every query on it must filter on ``organization`` explicitly.
    """

    class Role(models.TextChoices):
        OWNER = "owner", "Propriétaire"
        PLANNER = "planner", "Wedding planner"
        ASSISTANT = "assistant", "Assistant"
        ACCOUNTANT = "accountant", "Comptable"
        # Field roles (reservations-stock.md §12): no amounts, only their own modules.
        STOREKEEPER = "storekeeper", "Magasinier"
        TEAM_LEAD = "team_lead", "Chef d’équipe"
        STAFF = "staff", "Personnel"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    is_active = models.BooleanField(default=True)
    invited_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "organization"], name="unique_membership")
        ]
        indexes = [models.Index(fields=["organization", "is_active"])]

    def __str__(self) -> str:
        return f"{self.user_id} @ {self.organization_id} ({self.role})"


class TeamInvitation(models.Model):
    """Invitation to join a space with a role, accepted from an emailed link.

    Access-control table like ``Membership``: not tenant-scoped, always filtered on
    ``organization``. Only the SHA-256 of the token is stored.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="invitations"
    )
    email = models.EmailField()
    role = models.CharField(max_length=16, choices=Membership.Role.choices)
    token_hash = models.CharField(max_length=64, unique=True)
    invited_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "email"])]

    def __str__(self) -> str:
        return f"{self.email} → {self.organization_id} ({self.role})"

    def is_pending(self, now: datetime) -> bool:
        return self.accepted_at is None and self.cancelled_at is None and now < self.expires_at
