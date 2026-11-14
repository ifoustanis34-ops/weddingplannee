from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class PlatformAuditLog(models.Model):
    """What the Wedivo team did from the platform console (agencies, accounts, roles).

    Not a TenantModel: these actions span every agency. The agency concerned, when there is
    one, is kept to filter its history.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(max_length=64)
    target_type = models.CharField(max_length=64)
    target_id = models.CharField(max_length=64)
    # Name or email at the time of the action: the trace stays readable after a rename.
    target_label = models.CharField(max_length=200, blank=True)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    changes = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["-created_at"])]
        verbose_name = "action de la console"
        verbose_name_plural = "journal de la console"

    def __str__(self) -> str:
        return f"{self.action} {self.target_label or self.target_id}"
