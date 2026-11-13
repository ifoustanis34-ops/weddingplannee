"""Sending Web Push notifications (feedback 13/11/2026).

`notify()` is called by the business services (a mission assigned, a task to redo, a payment
received…) inside their transaction: the sending waits for the commit, then goes through Celery,
so a slow push service never delays the screen. Without VAPID keys nothing is sent (tests, a
fresh install): `enabled()` says so to the front, which then hides the switch.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.conf import settings
from django.db import transaction

from accounts.models import Membership
from core.tenant import require_current_organization


def enabled() -> bool:
    return bool(settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY)


def members_with_roles(roles: Iterable[str], *, exclude: Any = None) -> list[str]:
    """Active members of the current space with one of these roles."""
    users = Membership.objects.filter(
        organization=require_current_organization(), is_active=True, role__in=list(roles)
    ).values_list("user_id", flat=True)
    return [str(u) for u in users if exclude is None or str(u) != str(exclude)]


def notify(
    user_ids: Iterable[Any],
    *,
    title: str,
    body: str,
    url: str = "/",
    kind: str = "",
    tag: str | None = None,
) -> None:
    """Queue a notification for these users (every device of theirs), after the commit."""
    ids = sorted({str(u) for u in user_ids if u})
    if not ids or not enabled():
        return
    organization = require_current_organization()
    payload = {
        # The space in the title: a phone may receive the notifications of several agencies.
        "title": f"{organization.name} · {title}",
        "body": body,
        "url": url,
        "kind": kind,
        "tag": tag,
    }
    from .tasks import send_push

    transaction.on_commit(lambda: send_push.delay(ids, payload))
