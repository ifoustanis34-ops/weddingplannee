"""Daily summary of the open alerts to the owner (reservations-stock.md §5.4), switchable off."""

from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from accounts.models import Membership
from core.tenant import require_current_organization, tenant_context_for_id
from organizations.models import Organization

from . import services

logger = logging.getLogger(__name__)
SEVERITY_LABEL = {"critical": "Urgent", "serious": "Important", "warning": "À surveiller"}


def _line(row: dict[str, object]) -> str:
    label = SEVERITY_LABEL[str(row["severity"])]
    detail = (
        {
            "overdue_payment": "échéance de {amount} FCFA en retard de {days} j",
            "late_tasks": "{count} tâche(s) en retard",
            "wedding_unready": "{count} tâche(s) à finir, J-{days}",
        }
        .get(str(row["kind"]), "")
        .format(**{k: row.get(k, "") for k in ("amount", "days", "count")})
    )
    return f"• [{label}] {row['title']} — {detail}"


def send_digest() -> int:
    """In the active organization: one email per active owner. Returns the number of emails."""
    services.refresh()
    rows = services.sorted_open()
    if not rows:
        return 0
    organization = require_current_organization()
    owners = Membership.objects.filter(
        organization=organization, role=Membership.Role.OWNER, is_active=True
    ).select_related("user")
    body = "\n".join(_line(row) for row in rows)
    link = f"{settings.FRONTEND_URL.rstrip('/')}/"
    sent = 0
    for membership in owners:
        send_mail(
            subject=f"{len(rows)} alerte(s) aujourd’hui — {organization.name}",
            message=(
                f"Bonjour {membership.user.first_name},\n\n"
                f"Voici les alertes en cours dans votre espace :\n\n{body}\n\n"
                f"Tableau de bord : {link}\n\n"
                "Vous pouvez désactiver ce résumé dans Paramètres › Entreprise.\n\nL’équipe Wedivo"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[membership.user.email],
        )
        sent += 1
    return sent


@shared_task(queue="emails")  # type: ignore[untyped-decorator]
def send_daily_digests() -> int:
    """Every morning (beat), for the organizations that keep the summary on."""
    sent = 0
    ids = Organization.objects.filter(is_active=True, alert_digest=True).values_list(
        "pk", flat=True
    )
    for organization_id in ids:
        try:
            with tenant_context_for_id(organization_id):
                sent += send_digest()
        except Exception:  # one organization must never block the others
            logger.exception("Alert digest failed for organization %s", organization_id)
    return sent
