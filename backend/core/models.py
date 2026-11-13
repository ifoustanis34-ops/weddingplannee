from __future__ import annotations

import uuid
from typing import Any, ClassVar

from django.conf import settings
from django.db import models

from .tenant import require_current_organization


class TenantQuerySet(models.QuerySet[Any]):
    pass


class TenantManager(models.Manager[Any]):
    """Default manager of tenant models: always scoped to the active organization."""

    def get_queryset(self) -> TenantQuerySet:
        organization = require_current_organization()
        return TenantQuerySet(self.model, using=self._db).filter(organization=organization)

    def none(self) -> TenantQuerySet:
        """An empty queryset exposes nothing: allowed without an active organization."""
        return TenantQuerySet(self.model, using=self._db).none()


class AllTenantsManager(models.Manager[Any]):
    """Unscoped manager, reserved for administration jobs run inside ``bypass_tenant()``."""


class TenantModel(models.Model):
    """Base class of every business table (CLAUDE.md §5)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="+", db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    objects: ClassVar[TenantManager] = TenantManager()
    all_tenants: ClassVar[AllTenantsManager] = AllTenantsManager()

    class Meta:
        abstract = True
        # Related lookups and deletions must not depend on the active organization.
        base_manager_name = "all_tenants"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.organization_id:
            self.organization = require_current_organization()
        super().save(*args, **kwargs)


class AuditLog(TenantModel):
    """Trace of sensitive actions: payments, cancellations, role changes, deletions, exports."""

    action = models.CharField(max_length=64)
    target_type = models.CharField(max_length=64)
    target_id = models.CharField(max_length=64)
    changes = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )

    class Meta(TenantModel.Meta):
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.action} {self.target_type}:{self.target_id}"
