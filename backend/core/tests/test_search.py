from __future__ import annotations

from collections.abc import Callable
from datetime import date

from rest_framework.test import APIClient

from accounts.models import Membership, User
from core.tenant import tenant_context
from crm.models import Client
from crm.tests.factories import ClientFactory
from organizations.models import Organization
from quotes.models import Quote

URL = "/api/v1/search"


def _quote(customer: Client, number: str) -> Quote:
    quote: Quote = Quote.objects.create(
        client=customer,
        number=number,
        issue_date=date(2026, 10, 14),
        valid_until=date(2026, 11, 13),
        total=2_860_000,
        status=Quote.Status.SENT,
    )
    return quote


def test_finds_clients_and_quotes_of_the_current_organization(
    client_for: Callable[..., APIClient], org_a: Organization, owner_a: User
) -> None:
    with tenant_context(org_a):
        yao = ClientFactory.create(name="Jean-Marc Yao")
        ClientFactory.create(name="Grâce Bamba")
        ClientFactory.create(name="Yao supprimé", is_deleted=True)
        _quote(yao, "DV-2026-0044")

    data = client_for(owner_a, org_a).get(URL, {"q": "yao"}).json()

    assert [p["name"] for p in data["clients"]] == ["Jean-Marc Yao"]
    assert data["quotes"] == [
        {
            "id": data["quotes"][0]["id"],
            "number": "DV-2026-0044",
            "client_name": "Jean-Marc Yao",
            "status": "sent",
            "total": 2_860_000,
        }
    ]


def test_quote_number_and_short_terms(
    client_for: Callable[..., APIClient], org_a: Organization, owner_a: User
) -> None:
    with tenant_context(org_a):
        _quote(ClientFactory.create(name="Patricia Ouattara"), "DV-2026-0047")
    client = client_for(owner_a, org_a)

    assert [q["number"] for q in client.get(URL, {"q": "0047"}).json()["quotes"]] == [
        "DV-2026-0047"
    ]
    assert client.get(URL, {"q": "p"}).json() == {"clients": [], "quotes": []}


def test_every_role_can_search(
    client_for: Callable[..., APIClient],
    org_a: Organization,
    make_member: Callable[..., User],
) -> None:
    accountant = make_member(org_a, Membership.Role.ACCOUNTANT)
    assert client_for(accountant, org_a).get(URL, {"q": "ab"}).status_code == 200


def test_never_returns_another_organization(
    client_for: Callable[..., APIClient],
    org_a: Organization,
    org_b: Organization,
    owner_b: User,
) -> None:
    with tenant_context(org_a):
        _quote(ClientFactory.create(name="Secret Kouassi"), "DV-2026-0001")

    data = client_for(owner_b, org_b).get(URL, {"q": "Kouassi"}).json()

    assert data == {"clients": [], "quotes": []}


def test_requires_a_member(client_for: Callable[..., APIClient], org_a: Organization) -> None:
    assert client_for(None, org_a).get(URL, {"q": "yao"}).status_code in (401, 403)
