from __future__ import annotations

import json
import logging
from typing import Any

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import PushSubscription

logger = logging.getLogger(__name__)
GONE = {404, 410}  # the browser dropped the subscription: forget the device


def unread_counts(user_ids: list[str]) -> dict[str, int]:
    """Unread notifications of each user, every space together (one icon per device)."""
    from django.db.models import Count

    from core.tenant import bypass_tenant

    from .models import Notification

    with bypass_tenant():
        rows = (
            Notification.all_tenants.filter(user_id__in=user_ids, read_at__isnull=True)
            .values("user_id")
            .annotate(n=Count("pk"))
        )
        return {str(row["user_id"]): row["n"] for row in rows}


def deliver(user_ids: list[str], payload: dict[str, Any]) -> int:
    """Send to every device of these users; returns how many accepted the message."""
    from pywebpush import WebPushException, webpush

    sent = 0
    unread = unread_counts(user_ids)
    for subscription in PushSubscription.objects.filter(user_id__in=user_ids):
        # Each device shows its owner's unread count on the app icon (like WhatsApp).
        message = {**payload, "badge": unread.get(str(subscription.user_id), 0)}
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                },
                data=json.dumps(message),
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_SUBJECT},
                ttl=12 * 3600,
                timeout=10,
            )
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in GONE:
                subscription.delete()
            else:
                logger.warning("push failed", extra={"status": status, "user": user_ids})
            continue
        sent += 1
        subscription.last_success_at = timezone.now()
        subscription.save(update_fields=["last_success_at"])
    return sent


@shared_task(queue="default", ignore_result=True)  # type: ignore[untyped-decorator]
def send_push(user_ids: list[str], payload: dict[str, Any]) -> int:
    return deliver(user_ids, payload)
