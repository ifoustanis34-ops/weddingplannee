"""« Mon espace » (feedback 13/11/2026): a person's own figures, today's team for a lead."""

from __future__ import annotations

from collections.abc import Callable

from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Membership, User
from core.tenant import tenant_context
from organizations.models import Organization
from staff import services
from staff.models import StaffTask
from staff.tests.test_staff import _defaults, person, reservation  # noqa: F401

Role = Membership.Role


def test_a_person_sees_their_figures_and_never_an_amount(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
) -> None:
    today = reservation(org_a, owner_a, 0)
    account = make_member(org_a, Role.STAFF)
    linda = person(org_a, "Linda Abena", user=account, position="Serveuse")
    with tenant_context(org_a):
        mission, _ = services.assign(today, linda, step="event", role="Service", user=owner_a)
        services.check_in(mission, user=owner_a)
        StaffTask.objects.create(staff=linda, reservation=today, title="Dresser les tables")

    body = client_for(account, org_a).get(reverse("my-overview")).json()

    assert body["staff"]["name"] == "Linda Abena"
    assert body["missions_week"] == 1
    assert body["tasks"] == {"todo": 1, "done": 0, "validated": 0}
    assert sum(body["attendance"].values()) == 1
    assert len(body["hours_by_week"]) == services.WEEKS_OF_HOURS
    assert body["next_mission"] == str(mission.pk)
    assert body["team"] == []  # not a team lead
    assert "pay_rate" not in str(body) and "amount" not in str(body)

    missions = client_for(account, org_a).get(reverse("my-missions")).json()["missions"]
    assert [m["state"] for m in missions] == ["in_progress"]


def test_a_team_lead_sees_today_team(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
) -> None:
    today = reservation(org_a, owner_a, 0)
    lead_account = make_member(org_a, Role.TEAM_LEAD)
    didier = person(org_a, "Didier Kra", user=lead_account, position="Chef d’équipe")
    brice = person(org_a, "Brice Ndzana")
    with tenant_context(org_a):
        services.assign(today, didier, step="event", role="", user=owner_a)
        services.assign(today, brice, step="event", role="Installation", user=owner_a)

    team = client_for(lead_account, org_a).get(reverse("my-overview")).json()["team"]

    assert [(m["name"], m["role"], m["attendance"]) for m in team] == [
        ("Brice Ndzana", "Installation", None)
    ]


def test_an_account_without_record_gets_an_empty_space(
    client_for: Callable[..., APIClient], make_member: Callable[..., User], org_a: Organization
) -> None:
    account = make_member(org_a, Role.STAFF)
    assert client_for(account, org_a).get(reverse("my-overview")).json() == {"staff": None}
