"""Isolation between organizations: middleware, ORM manager and PostgreSQL RLS."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from django.db import connection, transaction
from django.db.utils import ProgrammingError
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Membership, User
from core.models import AuditLog
from core.tenant import TenantNotSetError, bypass_tenant, tenant_context
from organizations.models import Organization

pytestmark = pytest.mark.django_db

ORG_URL = reverse("organization")


def _log(organization: Organization, action: str) -> AuditLog:
    with tenant_context(organization):
        entry: AuditLog = AuditLog.objects.create(action=action, target_type="test", target_id="1")
    return entry


def _visible_actions_sql() -> list[str]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT action FROM core_auditlog ORDER BY action")
        return [row[0] for row in cursor.fetchall()]


# --- Middleware and membership ------------------------------------------------------------


def test_resolves_organization_from_subdomain(owner_a: User, org_a: Organization) -> None:
    from accounts.tokens import issue_tokens

    client = APIClient()
    client.cookies["wedivo_access"] = str(issue_tokens(owner_a).access_token)
    response = client.get(ORG_URL, HTTP_HOST="agence-a.wedivo.app")

    assert response.status_code == 200
    assert response.json()["slug"] == org_a.slug


def test_resolves_organization_from_dev_header(
    client_for: Callable[..., APIClient], owner_a: User, org_a: Organization
) -> None:
    response = client_for(owner_a, org_a).get(ORG_URL)

    assert response.status_code == 200
    assert response.json()["name"] == "Agence A"


def test_subdomain_wins_over_the_header(
    client_for: Callable[..., APIClient],
    owner_a: User,
    org_a: Organization,
    org_b: Organization,
) -> None:
    response = client_for(owner_a).get(
        ORG_URL, HTTP_HOST="agence-a.wedivo.app", HTTP_X_ORGANIZATION=org_b.slug
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Agence A"


def test_unknown_organization_returns_404(
    client_for: Callable[..., APIClient], owner_a: User
) -> None:
    client = client_for(owner_a)
    response = client.get(ORG_URL, HTTP_X_ORGANIZATION="inconnue")

    assert response.status_code == 404
    assert response.json()["code"] == "organization_not_found"


def test_inactive_organization_returns_404(
    client_for: Callable[..., APIClient], owner_a: User, org_a: Organization
) -> None:
    Organization.objects.filter(pk=org_a.pk).update(is_active=False)

    assert client_for(owner_a, org_a).get(ORG_URL).status_code == 404


def test_member_of_a_cannot_enter_space_b(
    client_for: Callable[..., APIClient], owner_a: User, org_b: Organization
) -> None:
    response = client_for(owner_a, org_b).get(ORG_URL)

    assert response.status_code == 403
    assert response.json()["code"] == "not_a_member"


def test_deactivated_member_is_refused(
    client_for: Callable[..., APIClient], owner_a: User, org_a: Organization
) -> None:
    Membership.objects.filter(user=owner_a).update(is_active=False)

    assert client_for(owner_a, org_a).get(ORG_URL).status_code == 403


def test_anonymous_request_is_unauthenticated(
    client_for: Callable[..., APIClient], org_a: Organization
) -> None:
    response = client_for(None, org_a).get(ORG_URL)

    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


def test_tenant_endpoint_without_organization_is_refused(
    client_for: Callable[..., APIClient], owner_a: User
) -> None:
    assert client_for(owner_a).get(ORG_URL).status_code == 403


def test_reserved_subdomain_is_not_a_tenant(org_a: Organization) -> None:
    response = APIClient().get(reverse("health"), HTTP_HOST="api.wedivo.app")

    assert response.status_code == 200


# --- ORM manager --------------------------------------------------------------------------


def test_manager_refuses_queries_without_active_organization(org_a: Organization) -> None:
    with pytest.raises(TenantNotSetError):
        list(AuditLog.objects.all())


def test_empty_queryset_needs_no_organization() -> None:
    assert list(AuditLog.objects.none()) == []


def test_manager_only_returns_current_organization_rows(
    org_a: Organization, org_b: Organization
) -> None:
    _log(org_a, "a.created")
    _log(org_b, "b.created")

    with tenant_context(org_a):
        assert list(AuditLog.objects.values_list("action", flat=True)) == ["a.created"]
    with tenant_context(org_b):
        assert list(AuditLog.objects.values_list("action", flat=True)) == ["b.created"]


def test_save_assigns_the_active_organization(org_a: Organization) -> None:
    entry = _log(org_a, "a.created")

    assert entry.organization_id == org_a.pk


# --- PostgreSQL Row-Level Security (raw SQL, below the ORM) -------------------------------


def test_rls_hides_other_organizations_rows_from_raw_sql(
    org_a: Organization, org_b: Organization
) -> None:
    _log(org_a, "a.created")
    _log(org_b, "b.created")

    with tenant_context(org_a):
        assert _visible_actions_sql() == ["a.created"]
    with tenant_context(org_b):
        assert _visible_actions_sql() == ["b.created"]


def test_rls_shows_nothing_without_active_organization(org_a: Organization) -> None:
    _log(org_a, "a.created")

    assert _visible_actions_sql() == []


def test_rls_refuses_writing_into_another_organization(
    org_a: Organization, org_b: Organization
) -> None:
    with tenant_context(org_a), pytest.raises(ProgrammingError), transaction.atomic():
        AuditLog.all_tenants.create(
            organization=org_b, action="intrusion", target_type="test", target_id="1"
        )


def test_rls_is_enforced_for_the_application_role() -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user")
        assert cursor.fetchone() == (False,), "The app must not connect as superuser/BYPASSRLS"
        cursor.execute(
            "SELECT relrowsecurity, relforcerowsecurity FROM pg_class"
            " WHERE relname = 'core_auditlog'"
        )
        assert cursor.fetchone() == (True, True)


def test_bypass_tenant_sees_every_organization(org_a: Organization, org_b: Organization) -> None:
    _log(org_a, "a.created")
    _log(org_b, "b.created")

    with bypass_tenant():
        assert sorted(AuditLog.all_tenants.values_list("action", flat=True)) == [
            "a.created",
            "b.created",
        ]
