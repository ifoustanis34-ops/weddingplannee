from __future__ import annotations

from typing import Any

from django.db import models
from rest_framework.request import Request

from .models import AuditLog


def client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return str(forwarded).split(",")[0].strip()
    remote = request.META.get("REMOTE_ADDR")
    return str(remote) if remote else None


def record(
    action: str,
    target: models.Model,
    *,
    request: Request | None = None,
    changes: dict[str, Any] | None = None,
) -> AuditLog:
    """Write an audit entry in the active organization."""
    actor = request.user if request is not None and request.user.is_authenticated else None
    entry: AuditLog = AuditLog.objects.create(
        action=action,
        target_type=target._meta.label_lower,
        target_id=str(target.pk),
        changes=changes or {},
        ip=client_ip(request),
        actor=actor,
        created_by=actor,
    )
    return entry
