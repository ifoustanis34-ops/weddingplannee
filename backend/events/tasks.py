from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

from core.tenant import tenant_context_for_id
from organizations.models import Organization

from . import services

logger = logging.getLogger(__name__)


@shared_task(queue="emails")  # type: ignore[untyped-decorator]
def notify_due_tasks() -> int:
    """Every morning (beat): J-2 email to the assignees of open tasks (CLAUDE.md §7.6)."""
    sent = 0
    for organization_id in Organization.objects.filter(is_active=True).values_list("pk", flat=True):
        try:
            with tenant_context_for_id(organization_id):
                sent += services.send_due_task_alerts(timezone.localdate())
        except Exception:  # one organization must never block the others
            logger.exception("Task alerts failed for organization %s", organization_id)
    return sent
