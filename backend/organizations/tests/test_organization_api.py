from __future__ import annotations

from collections.abc import Callable

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Membership, User
from core.models import AuditLog
from core.tenant import tenant_context
from organizations.models import Organization

pytestmark = pytest.mark.django_db

ORG_URL = reverse("organization")
MEMBERS_URL = reverse("organization-members")


@pytest.mark.parametrize("role", [role.value for role in Membership.Role])
def test_every_member_reads_the_organization(
    role: str,
    client_for: Callable[..., APIClient],
    org_a: Organization,
    make_member: Callable[..., User],
) -> None:
    response = client_for(make_member(org_a, role), org_a).get(ORG_URL)

    assert response.status_code == 200
    assert response.json()["timezone"] == "Africa/Abidjan"


def test_owner_updates_settings_and_change_is_audited(
    client_for: Callable[..., APIClient], owner_a: User, org_a: Organization
) -> None:
    response = client_for(owner_a, org_a).patch(
        ORG_URL, {"city": "Yamoussoukro", "quote_prefix": "me"}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["city"] == "Yamoussoukro"
    assert response.json()["quote_prefix"] == "ME"
    with tenant_context(org_a):
        entry = AuditLog.objects.get(action="organization.updated")
    assert entry.actor == owner_a
    assert entry.changes["city"] == {"from": "Abidjan", "to": "Yamoussoukro"}


@pytest.mark.parametrize("role", ["planner", "assistant", "accountant"])
def test_only_owner_can_change_settings(
    role: str,
    client_for: Callable[..., APIClient],
    org_a: Organization,
    make_member: Callable[..., User],
) -> None:
    response = client_for(make_member(org_a, role), org_a).patch(
        ORG_URL, {"city": "Bouaké"}, format="json"
    )

    assert response.status_code == 403
    assert response.json()["code"] == "role_read_only"


def test_plan_cannot_be_changed_through_settings(
    client_for: Callable[..., APIClient], owner_a: User, org_a: Organization
) -> None:
    """The offer has its own endpoint (trial rules); the address is checked like at sign-up
    (see test_team.py). Public quote links use FRONTEND_URL, so they survive an address change."""
    client_for(owner_a, org_a).patch(ORG_URL, {"plan": "agence"}, format="json")

    org_a.refresh_from_db()
    assert org_a.plan == "pro"


def test_invalid_timezone_is_explained(
    client_for: Callable[..., APIClient], owner_a: User, org_a: Organization
) -> None:
    response = client_for(owner_a, org_a).patch(
        ORG_URL, {"timezone": "Mars/Olympus"}, format="json"
    )

    assert response.status_code == 400
    assert response.json()["fields"] == {"timezone": ["Fuseau horaire inconnu."]}


def test_members_list_is_limited_to_the_current_organization(
    client_for: Callable[..., APIClient],
    owner_a: User,
    owner_b: User,
    org_a: Organization,
    make_member: Callable[..., User],
) -> None:
    make_member(org_a, Membership.Role.ACCOUNTANT, email="compta@agence-a.ci")

    response = client_for(owner_a, org_a).get(MEMBERS_URL)

    emails = {member["email"] for member in response.json()}
    assert emails == {"owner@agence-a.ci", "compta@agence-a.ci"}
    assert owner_b.email not in emails


def test_member_of_both_organizations_switches_space(
    client_for: Callable[..., APIClient],
    owner_a: User,
    org_a: Organization,
    org_b: Organization,
) -> None:
    Membership.objects.create(user=owner_a, organization=org_b, role=Membership.Role.PLANNER)

    assert client_for(owner_a, org_a).get(ORG_URL).json()["slug"] == "agence-a"
    assert client_for(owner_a, org_b).get(ORG_URL).json()["slug"] == "agence-b"
    assert (
        client_for(owner_a, org_b).patch(ORG_URL, {"city": "X"}, format="json").status_code == 403
    )
