"""Presentation mode (feedback 16/11/2026): role switch in fictitious agencies only."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.conf import settings as django_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Membership, User
from core.models import AuditLog
from core.tenant import tenant_context
from organizations.models import Organization

Role = Membership.Role


def test_closed_unless_demo_mode_and_listed_space(
    client_for: Callable[..., APIClient], owner_a: User, org_a: Organization, settings: Any
) -> None:
    settings.DEMO_MODE = False
    settings.DEMO_ORGANIZATIONS = [org_a.slug]
    client = client_for(owner_a, org_a)
    assert client.get(reverse("demo-config")).json() == {"enabled": False, "roles": []}
    assert client.post(reverse("demo-switch"), {"role": "planner"}).status_code == 403

    # Demo mode on, but a real agency (not listed): still closed.
    settings.DEMO_MODE = True
    settings.DEMO_ORGANIZATIONS = ["une-agence-fictive"]
    assert client.post(reverse("demo-switch"), {"role": "planner"}).status_code == 403


def test_switches_to_the_member_of_that_role_in_the_demo_space(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    owner_a: User,
    org_a: Organization,
    org_b: Organization,
    settings: Any,
) -> None:
    settings.DEMO_MODE = True
    settings.DEMO_ORGANIZATIONS = [org_a.slug]
    storekeeper = make_member(org_a, Role.STOREKEEPER, full_name="Joël Mbarga")
    make_member(org_b, Role.PLANNER)  # another agency: never reachable from here
    client = client_for(owner_a, org_a)

    config = client.get(reverse("demo-config")).json()
    assert config["enabled"] is True and set(config["roles"]) == {"storekeeper", "owner"}

    response = client.post(reverse("demo-switch"), {"role": "storekeeper"})
    assert response.status_code == 200
    assert response.json()["user"]["full_name"] == "Joël Mbarga"
    assert django_settings.JWT_ACCESS_COOKIE in response.cookies
    with tenant_context(org_a):
        assert AuditLog.objects.filter(action="demo.role_switched").exists()
    assert storekeeper.memberships.get(organization=org_a).role == "storekeeper"

    # No planner in this demo space (the other agency's planner is out of reach).
    assert client.post(reverse("demo-switch"), {"role": "planner"}).status_code == 404
