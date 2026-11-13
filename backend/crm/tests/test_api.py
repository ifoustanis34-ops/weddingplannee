from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.db import connection
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Membership, User
from contracts import services as contract_services
from contracts.models import Contract
from core.models import AuditLog
from core.tenant import tenant_context
from crm.models import Client
from crm.tests.factories import ClientFactory
from organizations.models import Organization
from quotes import services as quote_services

pytestmark = pytest.mark.django_db

LIST_URL = reverse("client-list")


def detail(client: Client) -> str:
    return reverse("client-detail", args=[client.pk])


def make_client(organization: Organization, **kwargs: Any) -> Client:
    with tenant_context(organization):
        client: Client = ClientFactory.create(**kwargs)
    return client


def make_contract(org: Organization, user: User, client: Client, total: int) -> Contract:
    with tenant_context(org):
        quote = quote_services.create_quote(
            {"client": client, "wedding_date": timezone.localdate() + timedelta(days=60)},
            [
                quote_services.LineInput(
                    label="Location de matériel",
                    unit="flat",
                    unit_price=total,
                    quantity=Decimal(1),
                )
            ],
            user=user,
        )
        quote_services.accept_quote(quote, user=user)
        return quote_services.convert_to_contract(quote, user=user)


@pytest.fixture
def owner_client(
    client_for: Callable[..., APIClient], owner_a: User, org_a: Organization
) -> APIClient:
    return client_for(owner_a, org_a)


# --- CRUD -------------------------------------------------------------------------------------


def test_create_and_list_a_client(owner_client: APIClient) -> None:
    response = owner_client.post(
        LIST_URL,
        {
            "name": "Société Orange Events",
            "company": "Orange Events SARL",
            "phone": "+237 6 99 12 34 56",
            "phone_alt": "+237 6 77 00 11 22",
            "email": "Contact@Orange-Events.cm",
            "address": "Bonapriso, Douala",
            "preferences": "Nappes blanches, chaises Chiavari",
        },
        format="json",
    )

    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["email"] == "contact@orange-events.cm"
    assert body["order_count"] == 0
    assert body["revenue"] == 0
    assert "status" not in body and "source" not in body
    listed = owner_client.get(LIST_URL).json()["results"]
    assert [c["name"] for c in listed] == ["Société Orange Events"]


def test_name_is_required(owner_client: APIClient) -> None:
    response = owner_client.post(LIST_URL, {"name": "  "}, format="json")

    assert response.status_code == 400
    assert "name" in response.json()["fields"]


def test_archived_clients_leave_the_list(owner_client: APIClient, org_a: Organization) -> None:
    make_client(org_a, name="Famille Ekotto")
    archived = make_client(org_a, name="Ancien prospect", is_archived=True)

    names = [c["name"] for c in owner_client.get(LIST_URL).json()["results"]]
    assert names == ["Famille Ekotto"]
    shown = owner_client.get(LIST_URL, {"archived": "true"}).json()["results"]
    assert [c["id"] for c in shown] == [str(archived.pk)]
    # Archived, not lost: still reachable by its link.
    assert owner_client.get(detail(archived)).status_code == 200


def test_search_by_name_company_and_phone(owner_client: APIClient, org_a: Organization) -> None:
    make_client(org_a, name="Mme Ngo Bassong", phone="+237 6 55 44 33 22")
    make_client(org_a, name="Paroisse Saint-Joseph", company="Diocèse de Douala")

    def found(term: str) -> list[str]:
        results = owner_client.get(LIST_URL, {"search": term}).json()["results"]
        return [c["name"] for c in results]

    assert found("bassong") == ["Mme Ngo Bassong"]
    assert found("diocèse") == ["Paroisse Saint-Joseph"]
    assert found("55 44 33") == ["Mme Ngo Bassong"]


def test_update_and_soft_delete(owner_client: APIClient, org_a: Organization) -> None:
    client = make_client(org_a)

    patched = owner_client.patch(detail(client), {"notes": "Paie en deux fois"}, format="json")
    assert patched.json()["notes"] == "Paie en deux fois"

    assert owner_client.delete(detail(client)).status_code == 204
    assert owner_client.get(detail(client)).status_code == 404
    with tenant_context(org_a):
        assert Client.objects.filter(pk=client.pk, is_deleted=True).exists()
        assert AuditLog.objects.filter(action="client.deleted").exists()


# --- Indicators -------------------------------------------------------------------------------


def test_orders_revenue_and_balance_due(
    owner_client: APIClient, org_a: Organization, owner_a: User
) -> None:
    big = make_client(org_a, name="Agence Lumière Douala")
    small = make_client(org_a, name="Famille Ekotto")
    first = make_contract(org_a, owner_a, big, 1_500_000)
    make_contract(org_a, owner_a, big, 500_000)
    make_contract(org_a, owner_a, small, 300_000)
    with tenant_context(org_a):
        contract_services.record_payment(
            first, amount=500_000, method="cash", user=owner_a, paid_at=timezone.localdate()
        )

    body = owner_client.get(detail(big)).json()
    assert body["order_count"] == 2
    assert body["revenue"] == 2_000_000
    assert body["collected"] == 500_000
    assert body["balance_due"] == 1_500_000
    assert body["last_order_at"] is not None

    by_balance = owner_client.get(LIST_URL, {"ordering": "-balance_due"}).json()["results"]
    assert [c["name"] for c in by_balance] == ["Agence Lumière Douala", "Famille Ekotto"]

    history = owner_client.get(reverse("client-history", args=[big.pk])).json()
    assert len(history["contracts"]) == 2
    assert len(history["quotes"]) == 2
    assert [p["amount"] for p in history["payments"]] == [500_000]


def test_a_client_who_signs_leaves_the_archive(org_a: Organization, owner_a: User) -> None:
    client = make_client(org_a, is_archived=True)

    make_contract(org_a, owner_a, client, 200_000)

    with tenant_context(org_a):
        client.refresh_from_db()
    assert client.is_archived is False


def test_assistant_sees_no_amounts(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
) -> None:
    client = make_client(org_a, name="B")
    other = make_client(org_a, name="A")
    make_contract(org_a, owner_a, client, 900_000)
    assistant = client_for(make_member(org_a, Membership.Role.ASSISTANT), org_a)

    body = assistant.get(detail(client)).json()
    assert body["revenue"] is None and body["balance_due"] is None
    history = assistant.get(reverse("client-history", args=[client.pk])).json()
    assert history["payments"] == []
    assert history["contracts"][0]["total"] is None
    # Sorting by an amount it cannot see falls back to the name: no leak through the order.
    ordered = assistant.get(LIST_URL, {"ordering": "-revenue"}).json()["results"]
    assert [c["id"] for c in ordered] == [str(other.pk), str(client.pk)]


# --- Roles and isolation ----------------------------------------------------------------------


def test_assistant_edits_but_cannot_delete(
    client_for: Callable[..., APIClient], make_member: Callable[..., User], org_a: Organization
) -> None:
    client = make_client(org_a)
    assistant = client_for(make_member(org_a, Membership.Role.ASSISTANT), org_a)

    assert assistant.patch(detail(client), {"notes": "ok"}, format="json").status_code == 200
    assert assistant.delete(detail(client)).status_code == 403


def test_accountant_only_reads(
    client_for: Callable[..., APIClient], make_member: Callable[..., User], org_a: Organization
) -> None:
    client = make_client(org_a)
    accountant = client_for(make_member(org_a, Membership.Role.ACCOUNTANT), org_a)

    assert accountant.get(detail(client)).status_code == 200
    assert accountant.patch(detail(client), {"notes": "x"}, format="json").status_code == 403
    assert accountant.post(LIST_URL, {"name": "X"}, format="json").status_code == 403


def test_organization_b_cannot_reach_clients_of_a(
    client_for: Callable[..., APIClient],
    org_a: Organization,
    org_b: Organization,
    owner_b: User,
) -> None:
    client = make_client(org_a)
    other = client_for(owner_b, org_b)

    assert other.get(LIST_URL).json()["results"] == []
    assert other.get(detail(client)).status_code == 404
    assert other.patch(detail(client), {"name": "Pirate"}, format="json").status_code == 404
    assert other.delete(detail(client)).status_code == 404
    assert other.get(reverse("client-history", args=[client.pk])).status_code == 404
    with tenant_context(org_a):
        client.refresh_from_db()
    assert client.name != "Pirate" and client.is_deleted is False


# --- Removal of prospection and reminders (reservations-stock.md §2, §13) -------------------


@pytest.mark.parametrize(
    "name", ["prospect-list", "prospect-import", "reminder-jobs", "reminder-rules"]
)
def test_prospection_and_reminder_routes_are_gone(name: str) -> None:
    with pytest.raises(NoReverseMatch):
        reverse(name)


@pytest.mark.parametrize(
    "path", ["/api/v1/prospects", "/api/v1/reminders/jobs", "/api/v1/reminders/rules"]
)
def test_old_urls_answer_404(owner_client: APIClient, path: str) -> None:
    assert owner_client.get(path).status_code == 404


def test_removed_tables_are_dropped_and_clients_are_isolated() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT relname FROM pg_class WHERE relkind = 'r' AND relname IN"
            " ('crm_prospect', 'crm_interaction', 'reminders_reminderrule',"
            " 'reminders_reminderjob')"
        )
        assert cursor.fetchall() == []
        cursor.execute(
            "SELECT count(*) FROM pg_class WHERE relname = 'crm_client'"
            " AND relrowsecurity AND relforcerowsecurity"
        )
        assert cursor.fetchone() == (1,)


def test_signup_creates_no_reminder_rule(owner_client: APIClient) -> None:
    from django.apps import apps

    assert not apps.is_installed("reminders")
    from config.settings.base import CELERY_BEAT_SCHEDULE

    tasks = [entry["task"] for entry in CELERY_BEAT_SCHEDULE.values()]
    assert not any("reminder" in str(t) or "stale" in str(t) for t in tasks)
