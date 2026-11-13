"""Ticket batches (docs/specs/devis-billets.md §6): Celery queue `pdf`, progress in the cache."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from celery import shared_task
from django.core.cache import cache

from core.tenant import tenant_context_for_id

from . import services
from .models import Guest

logger = logging.getLogger(__name__)
PROGRESS_TTL = 3600


def progress_key(organization_id: str, batch_id: str) -> str:
    return f"org:{organization_id}:ticket-batch:{batch_id}"


def get_progress(organization_id: str, batch_id: str) -> dict[str, Any] | None:
    value: dict[str, Any] | None = cache.get(progress_key(organization_id, batch_id))
    return value


def start_batch(organization_id: str, wedding_id: str, guest_ids: list[str], user_id: str) -> str:
    batch_id = uuid.uuid4().hex
    cache.set(
        progress_key(organization_id, batch_id),
        {
            "total": len(guest_ids),
            "done": 0,
            "failed": 0,
            "status": "running",
            "wedding": wedding_id,
        },
        PROGRESS_TTL,
    )
    generate_tickets.delay(organization_id, batch_id, guest_ids, user_id)
    return batch_id


@shared_task(queue="pdf")  # type: ignore[untyped-decorator]
def generate_tickets(
    organization_id: str, batch_id: str, guest_ids: list[str], user_id: str
) -> None:
    """Issue and render the tickets one by one; a failure is counted, the batch goes on."""
    from accounts.models import User

    key = progress_key(organization_id, batch_id)
    with tenant_context_for_id(organization_id):
        user = User.objects.filter(pk=user_id).first()
        state = cache.get(key) or {"total": len(guest_ids), "done": 0, "failed": 0}
        for guest in Guest.objects.select_related("wedding").filter(pk__in=guest_ids):
            try:
                services.generate(services.issue_ticket(guest, user=user))
                state["done"] += 1
            except Exception:
                logger.exception("ticket generation failed", extra={"guest": str(guest.pk)})
                state["failed"] += 1
            cache.set(key, state, PROGRESS_TTL)
        state["status"] = "done"
        cache.set(key, state, PROGRESS_TTL)
