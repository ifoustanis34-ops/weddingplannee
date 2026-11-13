"""Alert center and field roles (reservations-stock.md §2, §5.4, §12)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from django.core import mail
from django.db import connection
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Membership, User
from alerts import services
from alerts.models import Alert
from alerts.tasks import send_daily_digests
from contracts import services as contract_services
from contracts.models import Contract
from core.tenant import tenant_context
from events.models import Task, Wedding
from finance.tests.test_finance import make_contract
from organizations.models import Organization

pytestmark = pytest.mark.django_db
LIST = reverse("alert-list")


def overdue_contract(org: Organization, owner: User, days_late: int) -> Contract:
    """A 1 000 000 contract whose 300 000 deposit was due ``days_late`` days ago."""
    contract = make_contract(org, owner, 1_000_000)
    with tenant_context(org):
        deposit = contract.schedule.order_by("position").first()
        assert deposit is not None
        deposit.due_date = timezone.localdate() - timedelta(days=days_late)
        deposit.save()
    return contract


def open_kinds(org: Organization) -> dict[str, Alert]:
    with tenant_context(org):
        services.refresh()
        return {a.kind: a for a in services.open_alerts()}


# --- Life cycle ---------------------------------------------------------------------------------


def test_an_overdue_installment_opens_then_resolves_itself(
    org_a: Organization, owner_a: User
) -> None:
    contract = overdue_contract(org_a, owner_a, days_late=3)

    alert = open_kinds(org_a)[Alert.Kind.OVERDUE_PAYMENT]
    assert alert.severity == Alert.Severity.SERIOUS
    assert alert.data["amount"] == 300_000 and alert.data["days"] == 3

    with tenant_context(org_a):
        contract.schedule.filter(label="Acompte").update(
            due_date=timezone.localdate() - timedelta(days=9)
        )
    assert open_kinds(org_a)[Alert.Kind.OVERDUE_PAYMENT].severity == Alert.Severity.CRITICAL

    with tenant_context(org_a):
        contract_services.record_payment(
            contract, amount=300_000, method="cash", user=owner_a, paid_at=timezone.localdate()
        )
    assert Alert.Kind.OVERDUE_PAYMENT not in open_kinds(org_a)
    with tenant_context(org_a):
        assert Alert.objects.get(kind=Alert.Kind.OVERDUE_PAYMENT).resolved_at is not None


def test_late_tasks_and_an_unready_wedding(org_a: Organization, owner_a: User) -> None:
    contract = make_contract(org_a, owner_a, 1_000_000)
    with tenant_context(org_a):
        wedding = Wedding.objects.get(contract=contract)
        wedding.date = timezone.localdate() + timedelta(days=4)
        wedding.save()
        Task.objects.create(
            wedding=wedding, title="Plan de table", due_date=timezone.localdate() - timedelta(1)
        )

    kinds = open_kinds(org_a)
    assert kinds[Alert.Kind.LATE_TASKS].data["count"] == 1
    assert kinds[Alert.Kind.WEDDING_UNREADY].data["days"] == 4


def test_a_dismissed_alert_stays_away_while_its_situation_lasts(
    client_for: Callable[..., APIClient], org_a: Organization, owner_a: User
) -> None:
    overdue_contract(org_a, owner_a, days_late=2)
    client = client_for(owner_a, org_a)
    listed = client.get(LIST).json()
    assert listed["count"] == 1
    alert_id = listed["results"][0]["id"]

    assert client.post(reverse("alert-dismiss", args=[alert_id])).status_code == 200

    with tenant_context(org_a):
        services.refresh()
    assert client.get(LIST).json()["count"] == 0
    assert client.post(reverse("alert-dismiss", args=[alert_id])).status_code == 404


def test_a_payment_refreshes_the_alerts_at_once(
    client_for: Callable[..., APIClient], org_a: Organization, owner_a: User, settings: Any
) -> None:
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "a"},
        "locks": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "b"},
    }
    contract = overdue_contract(org_a, owner_a, days_late=2)
    client = client_for(owner_a, org_a)
    assert client.get(LIST).json()["count"] == 1

    with tenant_context(org_a):
        contract_services.record_payment(
            contract, amount=300_000, method="cash", user=owner_a, paid_at=timezone.localdate()
        )

    assert client.get(LIST).json()["count"] == 0  # not 5 minutes later


# --- Roles --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("role", "sees_money", "sees_tasks"),
    [
        (Membership.Role.OWNER, True, True),
        (Membership.Role.PLANNER, True, True),
        (Membership.Role.ASSISTANT, False, True),
        (Membership.Role.TEAM_LEAD, False, True),
        (Membership.Role.STOREKEEPER, False, False),
        (Membership.Role.STAFF, False, False),
    ],
)
def test_each_role_gets_its_own_alerts(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
    role: str,
    sees_money: bool,
    sees_tasks: bool,
) -> None:
    contract = overdue_contract(org_a, owner_a, days_late=2)
    with tenant_context(org_a):
        Task.objects.create(
            wedding=Wedding.objects.get(contract=contract),
            title="Plan de table",
            due_date=timezone.localdate() - timedelta(days=1),
        )
    member = owner_a if role == Membership.Role.OWNER else make_member(org_a, role)

    kinds = {a["kind"] for a in client_for(member, org_a).get(LIST).json()["results"]}

    assert ("overdue_payment" in kinds) is sees_money
    assert ("late_tasks" in kinds) is sees_tasks


@pytest.mark.parametrize(
    "role", [Membership.Role.STOREKEEPER, Membership.Role.TEAM_LEAD, Membership.Role.STAFF]
)
def test_field_roles_only_reach_their_own_modules(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
    role: str,
) -> None:
    make_contract(org_a, owner_a, 1_000_000)
    client = client_for(make_member(org_a, role), org_a)

    for url in (
        "/api/v1/clients",
        "/api/v1/quotes",
        "/api/v1/contracts",
        "/api/v1/weddings",
        "/api/v1/vendors",
        "/api/v1/catalog/categories",
        "/api/v1/search?q=awa",
    ):
        assert client.get(url).status_code == 403, url
    assert client.get("/api/v1/organization").status_code == 200
    dashboard = client.get(reverse("dashboard-summary")).json()
    assert dashboard["signature"] is None and dashboard["balances"] is None
    assert all(row["revenue"] is None for row in dashboard["top_services"])


def test_the_owner_can_invite_a_storekeeper(
    client_for: Callable[..., APIClient], org_a: Organization, owner_a: User
) -> None:
    response = client_for(owner_a, org_a).post(
        "/api/v1/organization/invitations",
        {"email": "joel.mbarga@maison-elegance.ci", "role": "storekeeper"},
        format="json",
    )

    assert response.status_code == 201, response.json()


# --- Isolation, digest, RLS ---------------------------------------------------------------------


def test_organization_b_cannot_see_or_dismiss_alerts_of_a(
    client_for: Callable[..., APIClient],
    org_a: Organization,
    owner_a: User,
    org_b: Organization,
    owner_b: User,
) -> None:
    overdue_contract(org_a, owner_a, days_late=2)
    alert_id = client_for(owner_a, org_a).get(LIST).json()["results"][0]["id"]
    other = client_for(owner_b, org_b)

    assert other.get(LIST).json()["count"] == 0
    assert other.post(reverse("alert-dismiss", args=[alert_id])).status_code == 404


def test_daily_digest_goes_to_the_owner_unless_switched_off(
    org_a: Organization, owner_a: User, org_b: Organization, owner_b: User
) -> None:
    overdue_contract(org_a, owner_a, days_late=9)
    overdue_contract(org_b, owner_b, days_late=9)
    Organization.objects.filter(pk=org_b.pk).update(alert_digest=False)

    assert send_daily_digests() == 1
    assert mail.outbox[-1].to == [owner_a.email]
    assert "[Urgent]" in mail.outbox[-1].body
    assert "300 000" in mail.outbox[-1].body or "300000" in mail.outbox[-1].body


def test_alerts_are_under_row_level_security() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM pg_class WHERE relname = 'alerts_alert'"
            " AND relrowsecurity AND relforcerowsecurity"
        )
        assert cursor.fetchone() == (1,)
