"""Vendor directory and bookings (CLAUDE.md §7.7, complement §13)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Membership, User
from organizations.models import Organization


@pytest.fixture
def client(client_for: Callable[..., APIClient], owner_a: User, org_a: Organization) -> APIClient:
    return client_for(owner_a, org_a)


def vendor(client: APIClient, **extra: Any) -> dict[str, Any]:
    response = client.post(
        reverse("vendor-list"),
        {
            "name": "Fleurs d’Ébène",
            "category": "decoration",
            "phone": "+225 07 22 18 90 45",
            "services": "Décoration florale et bouquets",
            **extra,
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    body: dict[str, Any] = response.json()
    return body


def wedding(client: APIClient) -> dict[str, Any]:
    body: dict[str, Any] = client.post(
        reverse("wedding-list"),
        {"title": "Aïcha & Serge", "date": (date.today() + timedelta(25)).isoformat()},
        format="json",
    ).json()
    return body


def book(client: APIClient, wedding_id: str, vendor_id: str, **extra: Any) -> Any:
    return client.post(
        reverse("wedding-vendors", args=[wedding_id]),
        {
            "vendor": vendor_id,
            "service": "Décoration de salle",
            "cost": 900_000,
            "paid_amount": 450_000,
            **extra,
        },
        format="json",
    )


def test_bookings_feed_collaborations_and_amount_due(client: APIClient) -> None:
    fleurs = vendor(client)
    first, second = wedding(client), wedding(client)
    assert book(client, first["id"], fleurs["id"]).status_code == 201
    book(client, second["id"], fleurs["id"], cost=300_000, paid_amount=300_000)

    row = client.get(reverse("vendor-list")).json()[0]
    assert (row["collaborations"], row["due"]) == (2, 450_000)
    detail = client.get(reverse("wedding-detail", args=[first["id"]])).json()
    assert detail["vendors_count"] == 1
    due = client.get(reverse("finance-summary")).json()["vendors_due"]
    assert due == [
        {
            "id": fleurs["id"],
            "name": "Fleurs d’Ébène",
            "category_label": "Décoration",
            "due": 450_000,
        }
    ]


def test_paid_cannot_exceed_the_cost(client: APIClient) -> None:
    fleurs = vendor(client)
    assert (
        book(client, wedding(client)["id"], fleurs["id"], paid_amount=1_000_000).status_code == 400
    )


def test_a_supplier_describes_its_services_and_has_no_rating(client: APIClient) -> None:
    """Feedback 13/11/2026: the 1-5 rating is gone, the services offered take its place."""
    created = vendor(client)
    assert created["services"] == "Décoration florale et bouquets"
    assert "rating" not in created


def test_the_assistant_sees_the_vendors_but_not_the_money(
    client: APIClient,
    client_for: Callable[..., APIClient],
    org_a: Organization,
    make_member: Callable[..., User],
) -> None:
    fleurs = vendor(client)
    event = wedding(client)
    book(client, event["id"], fleurs["id"])
    assistant = client_for(make_member(org_a, Membership.Role.ASSISTANT), org_a)

    row = assistant.get(reverse("vendor-list")).json()[0]
    assert "due" not in row and row["collaborations"] == 1
    booked = assistant.get(reverse("wedding-vendors", args=[event["id"]])).json()[0]
    assert "cost" not in booked and booked["vendor_name"] == "Fleurs d’Ébène"
    # Amounts sent by the assistant are ignored.
    created = book(assistant, event["id"], fleurs["id"], cost=5, paid_amount=5).json()
    assert "cost" not in created


def test_vendors_stay_in_their_organization(
    client: APIClient,
    client_for: Callable[..., APIClient],
    org_b: Organization,
    owner_b: User,
) -> None:
    fleurs = vendor(client)
    event = wedding(client)
    booking = book(client, event["id"], fleurs["id"]).json()
    client_b = client_for(owner_b, org_b)

    assert client_b.get(reverse("vendor-list")).json() == []
    assert (
        client_b.patch(reverse("vendor-detail", args=[fleurs["id"]]), {"name": "x"}).status_code
        == 404
    )
    assert (
        client_b.delete(reverse("vendor-assignment-detail", args=[booking["id"]])).status_code
        == 404
    )
    other_wedding = wedding(client_b)
    # A vendor of org A cannot be booked on a wedding of org B.
    assert book(client_b, other_wedding["id"], fleurs["id"]).status_code == 400


def test_a_supplier_keeps_its_complete_record(client: APIClient) -> None:
    """Feedback 13/11/2026: « Fournisseurs » with contact, address, NIU, RCCM and payment."""
    created = vendor(
        client,
        name="Sono Pro Cameroun",
        category="sound",
        contact_name="Ferdinand Tagne",
        phone="+237 671 09 44 56",
        whatsapp="+237 671 09 44 56",
        city="Douala",
        address="Zone industrielle de Bassa",
        tax_id="M131412341010J",
        trade_register="RC/DLA/2014/B/0457",
        payment_terms="Paiement à 30 jours sur facture",
        mobile_money="+237 671 09 44 56",
        bank_details="UBA Cameroun — 10033 05201 12345678901 03",
    )

    assert created["category_label"] == "Sonorisation et lumière"
    assert created["contact_name"] == "Ferdinand Tagne"
    assert created["tax_id"] == "M131412341010J"
    assert created["trade_register"] == "RC/DLA/2014/B/0457"
    assert created["payment_terms"] == "Paiement à 30 jours sur facture"


def test_the_demo_suppliers_are_complete_and_cameroonian(org_a: Organization) -> None:
    from core.management.commands import demo_vendors
    from core.tenant import tenant_context
    from vendors.models import Vendor

    with tenant_context(org_a):
        Vendor.objects.create(name="Fleurs d’Ébène", category="decoration", phone="+225 07 22")
        demo_vendors.seed()
        again = demo_vendors.seed()  # idempotent
        suppliers = list(Vendor.objects.all())

    assert again == 0
    assert len(suppliers) == len(demo_vendors.SUPPLIERS)
    assert all(s.phone.startswith("+237") and s.contact_name and s.city for s in suppliers)
    flowers = next(s for s in suppliers if s.name == "Fleurs d’Ébène")
    assert flowers.category == "decoration"  # what the agency chose is kept
    assert flowers.tax_id


def test_partners_and_suppliers_share_one_directory(client: APIClient) -> None:
    """Feedback 13/11/2026: « Partenaires et fournisseurs », filtered by kind."""
    supplier = vendor(client)
    partner = vendor(client, name="Location Matériel Bonabéri", category="rental", kind="partner")

    assert supplier["kind"] == "supplier" and supplier["kind_label"] == "Fournisseur"
    assert partner["kind_label"] == "Partenaire"
    partners = client.get(reverse("vendor-list"), {"kind": "partner"}).json()
    assert [v["name"] for v in partners] == ["Location Matériel Bonabéri"]
    assert len(client.get(reverse("vendor-list")).json()) == 2
