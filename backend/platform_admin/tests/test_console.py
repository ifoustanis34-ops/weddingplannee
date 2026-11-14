"""Platform console (super-admin, feedback 14/11/2026)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Membership, User
from organizations.models import Organization
from platform_admin.models import PlatformAuditLog
from tests.factories import DEFAULT_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db

Role = Membership.Role


@pytest.fixture
def admin_user() -> User:
    return UserFactory.create(email="equipe@wedivo.app", is_staff=True, is_superuser=True)


@pytest.fixture
def console(admin_user: User, client_for: Callable[..., APIClient]) -> APIClient:
    return client_for(admin_user)


# --- Access ----------------------------------------------------------------------------------


def test_console_is_closed_to_agency_owners(
    owner_a: User, org_a: Organization, client_for: Callable[..., APIClient]
) -> None:
    client = client_for(owner_a, org_a)
    for url in ("/api/v1/platform/overview", "/api/v1/platform/agencies", "/api/v1/platform/users"):
        response = client.get(url)
        assert response.status_code == 403, url
        assert response.json()["code"] == "platform_admin_only"


def test_console_needs_a_session(client_for: Callable[..., APIClient]) -> None:
    assert client_for().get("/api/v1/platform/overview").status_code == 401


def test_session_says_who_opens_the_console(
    console: APIClient, owner_a: User, org_a: Organization, client_for: Callable[..., APIClient]
) -> None:
    assert console.get("/api/v1/auth/me").json()["user"]["is_platform_admin"] is True
    owner = client_for(owner_a, org_a).get("/api/v1/auth/me").json()
    assert owner["user"]["is_platform_admin"] is False


def test_console_works_without_any_agency(console: APIClient, admin_user: User) -> None:
    assert not admin_user.memberships.exists()
    assert console.get("/api/v1/platform/overview").status_code == 200


# --- Agencies --------------------------------------------------------------------------------


def test_lists_every_agency_with_owner_and_members(
    console: APIClient, org_a: Organization, org_b: Organization, owner_a: User, owner_b: User
) -> None:
    body = console.get("/api/v1/platform/agencies").json()
    assert body["count"] == 2
    by_slug = {agency["slug"]: agency for agency in body["results"]}
    assert by_slug["agence-a"]["owner_email"] == "owner@agence-a.ci"
    assert by_slug["agence-a"]["members_count"] == 1
    search = console.get("/api/v1/platform/agencies", {"search": "agence-b.ci"}).json()
    assert [a["slug"] for a in search["results"]] == ["agence-b"]


def test_creates_an_agency_with_its_owner_and_lifetime_access(
    console: APIClient, admin_user: User
) -> None:
    response = console.post(
        "/api/v1/platform/agencies",
        {
            "name": "Délices Événements",
            "slug": "delices-events",
            "city": "Douala",
            "country": "cm",
            "plan": "agence",
            "owner_full_name": "Paul Mbarga",
            "owner_email": "Paul@Delices.cm",
            "owner_password": "Provisoire-2026",
            "lifetime_access": True,
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["created_account"] is True
    assert body["agency"]["lifetime_access"] is True
    assert body["agency"]["owner_email"] == "paul@delices.cm"
    owner = User.objects.get(email="paul@delices.cm")
    assert owner.must_change_password and owner.check_password("Provisoire-2026")
    assert owner.memberships.get().role == Role.OWNER
    entry = PlatformAuditLog.objects.get(action="organization.created")
    assert entry.actor == admin_user and entry.organization is not None


def test_refuses_a_taken_address(console: APIClient, org_a: Organization) -> None:
    response = console.post(
        "/api/v1/platform/agencies",
        {
            "name": "Autre",
            "slug": "agence-a",
            "city": "Abidjan",
            "country": "CI",
            "owner_full_name": "X Y",
            "owner_email": "x@y.ci",
            "owner_password": "Provisoire-2026",
        },
        format="json",
    )
    assert response.status_code == 400
    assert "slug" in response.json()["fields"]


def test_lifetime_access_lets_the_agency_change_plan_after_the_trial(
    console: APIClient, org_a: Organization, owner_a: User, client_for: Callable[..., APIClient]
) -> None:
    Organization.objects.filter(pk=org_a.pk).update(
        trial_ends_at=timezone.now() - timedelta(days=1)
    )
    owner = client_for(owner_a, org_a)
    assert owner.post("/api/v1/organization/plan", {"plan": "agence"}).status_code == 400

    response = console.patch(
        f"/api/v1/platform/agencies/{org_a.pk}", {"lifetime_access": True}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["lifetime_access"] is True
    assert response.json()["lifetime_granted_at"] is not None
    assert owner.get("/api/v1/organization").json()["lifetime_access"] is True
    assert owner.post("/api/v1/organization/plan", {"plan": "agence"}).status_code == 200
    assert PlatformAuditLog.objects.filter(action="organization.lifetime_granted").exists()


def test_suspending_an_agency_closes_it_then_reactivating_opens_it(
    console: APIClient, org_a: Organization, owner_a: User, client_for: Callable[..., APIClient]
) -> None:
    owner = client_for(owner_a, org_a)
    assert owner.get("/api/v1/organization").status_code == 200  # puts the agency in cache

    response = console.patch(
        f"/api/v1/platform/agencies/{org_a.pk}",
        {"is_active": False, "suspension_reason": "Impayé"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["suspension_reason"] == "Impayé"
    assert owner.get("/api/v1/organization").status_code == 404
    assert client_for(owner_a).get("/api/v1/auth/me").json()["organizations"] == []

    console.patch(f"/api/v1/platform/agencies/{org_a.pk}", {"is_active": True}, format="json")
    assert owner.get("/api/v1/organization").status_code == 200
    actions = set(PlatformAuditLog.objects.values_list("action", flat=True))
    assert {"organization.suspended", "organization.reactivated"} <= actions


def test_lists_the_members_of_an_agency(
    console: APIClient, org_a: Organization, owner_a: User, make_member: Callable[..., User]
) -> None:
    make_member(org_a, Role.ACCOUNTANT, email="compta@agence-a.ci")
    members = console.get(f"/api/v1/platform/agencies/{org_a.pk}/members").json()
    assert {m["email"]: m["role"] for m in members} == {
        "owner@agence-a.ci": "owner",
        "compta@agence-a.ci": "accountant",
    }


# --- Accounts --------------------------------------------------------------------------------


def test_creates_an_account_in_an_agency(console: APIClient, org_a: Organization) -> None:
    response = console.post(
        "/api/v1/platform/users",
        {
            "full_name": "Awa Diallo",
            "email": "awa@agence-a.ci",
            "password": "Provisoire-2026",
            "organization_id": str(org_a.pk),
            "role": "planner",
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["must_change_password"] is True
    assert [(m["organization_slug"], m["role"]) for m in body["memberships"]] == [
        ("agence-a", "planner")
    ]


def test_account_in_an_agency_needs_a_role(console: APIClient, org_a: Organization) -> None:
    response = console.post(
        "/api/v1/platform/users",
        {
            "full_name": "Awa Diallo",
            "email": "awa@agence-a.ci",
            "password": "Provisoire-2026",
            "organization_id": str(org_a.pk),
        },
        format="json",
    )
    assert response.status_code == 400
    assert "role" in response.json()["fields"]


def test_deactivating_an_account_blocks_its_sign_in(
    console: APIClient, owner_a: User, org_a: Organization, client_for: Callable[..., APIClient]
) -> None:
    owner = client_for(owner_a, org_a)
    response = console.patch(
        f"/api/v1/platform/users/{owner_a.pk}", {"is_active": False}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert owner.get("/api/v1/organization").status_code == 401
    login = APIClient().post(
        "/api/v1/auth/login", {"email": owner_a.email, "password": DEFAULT_PASSWORD}
    )
    assert login.status_code == 401
    assert PlatformAuditLog.objects.filter(action="user.deactivated").exists()


def test_cannot_lock_oneself_out(console: APIClient, admin_user: User) -> None:
    url = f"/api/v1/platform/users/{admin_user.pk}"
    assert console.patch(url, {"is_active": False}, format="json").status_code == 400
    assert console.patch(url, {"is_platform_admin": False}, format="json").status_code == 400


def test_gives_and_takes_the_console(
    console: APIClient, owner_a: User, org_a: Organization, client_for: Callable[..., APIClient]
) -> None:
    url = f"/api/v1/platform/users/{owner_a.pk}"
    console.patch(url, {"is_platform_admin": True}, format="json")
    assert client_for(owner_a).get("/api/v1/platform/overview").status_code == 200
    console.patch(url, {"is_platform_admin": False}, format="json")
    assert client_for(owner_a).get("/api/v1/platform/overview").status_code == 403


def test_sets_a_temporary_password(console: APIClient, owner_a: User) -> None:
    response = console.post(
        f"/api/v1/platform/users/{owner_a.pk}/password", {"password": "Nouveau-2026!"}
    )
    assert response.status_code == 204
    owner_a.refresh_from_db()
    assert owner_a.check_password("Nouveau-2026!") and owner_a.must_change_password


def test_filters_accounts(
    console: APIClient, owner_a: User, admin_user: User, org_a: Organization
) -> None:
    admins = console.get("/api/v1/platform/users", {"status": "admins"}).json()
    assert [u["email"] for u in admins["results"]] == [admin_user.email]
    in_agency = console.get("/api/v1/platform/users", {"organization": str(org_a.pk)}).json()
    assert [u["email"] for u in in_agency["results"]] == [owner_a.email]


# --- Roles -----------------------------------------------------------------------------------


def test_naming_a_new_owner_transfers_the_agency(
    console: APIClient, org_a: Organization, owner_a: User, make_member: Callable[..., User]
) -> None:
    planner = make_member(org_a, Role.PLANNER, email="planner@agence-a.ci")
    membership = Membership.objects.get(user=planner, organization=org_a)
    response = console.patch(
        f"/api/v1/platform/memberships/{membership.pk}", {"role": "owner"}, format="json"
    )
    assert response.status_code == 200
    roles = dict(Membership.objects.filter(organization=org_a).values_list("user__email", "role"))
    assert roles == {"planner@agence-a.ci": "owner", "owner@agence-a.ci": "planner"}


def test_the_only_owner_cannot_be_removed(
    console: APIClient, org_a: Organization, owner_a: User
) -> None:
    membership = Membership.objects.get(user=owner_a, organization=org_a)
    url = f"/api/v1/platform/memberships/{membership.pk}"
    for payload in ({"role": "planner"}, {"is_active": False}):
        response = console.patch(url, payload, format="json")
        assert response.status_code == 400
        assert response.json()["code"] == "last_owner"


def test_places_an_existing_account_in_another_agency(
    console: APIClient, owner_a: User, org_b: Organization
) -> None:
    response = console.post(
        f"/api/v1/platform/users/{owner_a.pk}/memberships",
        {"organization_id": str(org_b.pk), "role": "accountant"},
        format="json",
    )
    assert response.status_code == 201
    assert sorted(m["organization_slug"] for m in response.json()["memberships"]) == [
        "agence-a",
        "agence-b",
    ]


def test_overview_counts(
    console: APIClient, org_a: Organization, org_b: Organization, owner_a: User
) -> None:
    Organization.objects.filter(pk=org_b.pk).update(is_active=False, lifetime_access=True)
    body = console.get("/api/v1/platform/overview").json()
    assert body["agencies"]["total"] == 2
    assert body["agencies"]["suspended"] == 1
    assert body["agencies"]["lifetime"] == 1
    assert body["users"]["admins"] == 1


def test_journal_lists_console_actions(console: APIClient, owner_a: User) -> None:
    console.patch(f"/api/v1/platform/users/{owner_a.pk}", {"phone": "+237 600"}, format="json")
    body = console.get("/api/v1/platform/journal").json()
    assert body["results"][0]["action"] == "user.updated"
    assert body["results"][0]["actor_name"]


# --- Command ---------------------------------------------------------------------------------


def test_command_creates_then_promotes(owner_a: User) -> None:
    out = StringIO()
    call_command("create_platform_admin", email="Chef@Wedivo.app", name="Chef Wedivo", stdout=out)
    chef = User.objects.get(email="chef@wedivo.app")
    assert chef.is_staff and chef.is_superuser and chef.must_change_password
    assert "Mot de passe provisoire" in out.getvalue()

    call_command("create_platform_admin", email=owner_a.email, stdout=StringIO())
    owner_a.refresh_from_db()
    assert owner_a.is_staff and owner_a.check_password(DEFAULT_PASSWORD)


def test_overview_follows_growth_and_trials_to_watch(
    console: APIClient, org_a: Organization, org_b: Organization, owner_a: User
) -> None:
    now = timezone.now()
    Organization.objects.filter(pk=org_a.pk).update(trial_ends_at=now + timedelta(days=2))
    Organization.objects.filter(pk=org_b.pk).update(is_active=False, suspended_at=now)
    body = console.get("/api/v1/platform/overview").json()
    assert len(body["growth"]) == 12
    assert body["growth"][-1]["agencies"] == 2
    assert {(w["slug"], w["kind"]) for w in body["watchlist"]} == {
        ("agence-a", "trial_ending"),
        ("agence-b", "suspended"),
    }
    assert body["agencies"]["engaged"] == 0
