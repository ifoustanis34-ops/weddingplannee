"""Web Push subscriptions (feedback 13/11/2026: notifications in real time on the phone).

A device belongs to a user, not to an organization (like `Membership`, a control table): one
phone receives the notifications of every space its user works in, each titled with the space.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from core.models import TenantModel


class PushSubscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_subscriptions"
    )
    # The push service's address for this browser (unique: one device, one row).
    endpoint = models.CharField(max_length=1000, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=64)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_success_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user_id} · {self.endpoint[:40]}…"


class Notification(TenantModel):
    """One notification of a person in a space (feedback 17/11/2026: like WhatsApp, an inbox with
    unread messages, a count on the app icon). Written by `push.notify()` for every event of the
    flow, whether or not the person's devices receive the push."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=32, blank=True)  # mission, task, payment, alert, …
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=500, blank=True)
    url = models.CharField(max_length=300, default="/")
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantModel.Meta):
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "user", "read_at"])]

    def __str__(self) -> str:
        return self.title
