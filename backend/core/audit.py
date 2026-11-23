from __future__ import annotations

import ipaddress
from typing import Any

from django.db import models
from django.http import HttpRequest
from rest_framework.request import Request

from .models import AuditLog


def _public(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)


def client_ip(request: Request | HttpRequest | None) -> str | None:
    """The visitor's address, as seen by our own proxies (anti-bot, 20/11/2026).

    ``X-Forwarded-For`` is « client, proxy1, proxy2 »: a bot can write any address on the left
    to dodge the limits, but our proxies only append. The rightmost public address is therefore
    the one our first proxy saw; on a private network (development) the leftmost one is kept.
    """
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        chain = [part.strip() for part in str(forwarded).split(",") if part.strip()]
        for address in reversed(chain):
            if _public(address):
                return address
        if chain:
            return chain[0]
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
