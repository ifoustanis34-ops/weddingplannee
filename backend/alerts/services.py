"""Keep the alerts in step with the situation (reservations-stock.md §5.4, §8)."""

from __future__ import annotations

from datetime import date
from typing import Any

from django.core.cache import cache
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from accounts.models import Membership, User
from core.tenant import require_current_organization
from finance.visibility import can_see_balances
from organizations.timezones import org_tz

from . import conditions
from .models import Alert

REFRESH_SECONDS = 300
SEVERITY_RANK = {"critical": 0, "serious": 1, "warning": 2}
MONEY_KINDS = frozenset({Alert.Kind.OVERDUE_PAYMENT, Alert.Kind.OVERDUE_INVOICE})
TASK_KINDS = frozenset({Alert.Kind.LATE_TASKS, Alert.Kind.WEDDING_UNREADY})
STOCK_KINDS = frozenset(
    {
        Alert.Kind.BELOW_THRESHOLD,
        Alert.Kind.MAINTENANCE_LATE,
        Alert.Kind.DAMAGED_UNIT,
        Alert.Kind.STOCK_SHORTAGE,
        Alert.Kind.LATE_RETURN,
    }
)
# Which alerts each role receives (§12): money only for balance roles; the storekeeper gets
# the stock alerts; the team lead the preparation of the events; staff nothing yet.
ROLE_KINDS: dict[str, frozenset[str]] = {
    Membership.Role.STOREKEEPER: STOCK_KINDS,
    Membership.Role.TEAM_LEAD: TASK_KINDS,
    Membership.Role.STAFF: frozenset(),
}


def stale_key(organization_id: Any) -> str:
    return f"org:{organization_id}:alerts:refreshed"


def local_today() -> date:
    return timezone.now().astimezone(org_tz(require_current_organization())).date()


@transaction.atomic
def refresh(today: date | None = None) -> int:
    """Open, update or resolve the alerts of the active organization. Returns how many are open.

    A dismissed alert stays dismissed while its situation lasts; a resolved one reopens if the
    situation comes back (same key).
    """
    today = today or local_today()
    now = timezone.now()
    existing = {alert.dedupe_key: alert for alert in Alert.objects.select_for_update()}
    seen: set[str] = set()
    for found in conditions.current(today):
        key = found["dedupe_key"]
        seen.add(key)
        alert = existing.get(key)
        if alert is None:
            created = Alert.objects.create(**found)
            # Urgent and important situations reach their people at once (17/11/2026).
            if created.severity in (Alert.Severity.CRITICAL, Alert.Severity.SERIOUS):
                notify_alert(created)
            continue
        for field in ("kind", "severity", "title", "subtitle", "occurred_on", "data"):
            setattr(alert, field, found[field])
        alert.resolved_at = None
        alert.save()
    for key, alert in existing.items():
        if key not in seen and alert.resolved_at is None:
            alert.resolved_at = now
            alert.save(update_fields=["resolved_at", "updated_at"])
    return Alert.objects.filter(resolved_at__isnull=True, dismissed_at__isnull=True).count()


def notify_alert(alert: Alert) -> None:
    """Push (13/11/2026): a new urgent alert reaches, at once, the roles that may see it."""
    from accounts.models import Membership
    from core.tenant import require_current_organization
    from notifications import push

    users = [
        m.user_id
        for m in Membership.objects.filter(
            organization=require_current_organization(), is_active=True
        )
        if visible_to(alert.kind, m.role)
    ]
    push.notify(
        users,
        title=(
            f"Urgent · {alert.title}"
            if alert.severity == Alert.Severity.CRITICAL
            else f"Important · {alert.title}"
        ),
        body=alert.subtitle,
        url="/",
        kind="alert",
        tag=f"alert-{alert.dedupe_key}",
    )


def refresh_if_stale() -> None:
    """At most every 5 minutes; any change to the money or the tasks makes it stale at once."""
    key = stale_key(require_current_organization().pk)
    if cache.get(key):
        return
    refresh()
    cache.set(key, True, REFRESH_SECONDS)


def open_alerts() -> QuerySet[Alert]:
    return Alert.objects.filter(resolved_at__isnull=True, dismissed_at__isnull=True)


def visible_to(alert_kind: str, role: str | None) -> bool:
    if role in ROLE_KINDS:
        return alert_kind in ROLE_KINDS[role]
    if alert_kind in MONEY_KINDS:
        return can_see_balances(role)
    return True


def as_dict(alert: Alert) -> dict[str, Any]:
    return {
        "id": str(alert.pk),
        "kind": alert.kind,
        "severity": alert.severity,
        "title": alert.title,
        "subtitle": alert.subtitle,
        "date": alert.occurred_on,
        "since": alert.created_at,
        "money": alert.kind in MONEY_KINDS,
        **alert.data,
    }


def sorted_open(role: str | None = None, *, filter_role: bool = False) -> list[dict[str, Any]]:
    """Open alerts, most urgent first (severity, then the oldest situation)."""
    rows = [as_dict(a) for a in open_alerts()]
    if filter_role:
        rows = [row for row in rows if visible_to(row["kind"], role)]
    rows.sort(key=lambda r: (SEVERITY_RANK[r["severity"]], r["date"] or date.max))
    return rows


def dismiss(alert: Alert, *, user: User) -> Alert:
    """« Marquer comme traitée »: the alert leaves the list while its situation lasts."""
    alert.dismissed_at = timezone.now()
    alert.dismissed_by = user
    alert.save(update_fields=["dismissed_at", "dismissed_by", "updated_at"])
    return alert
