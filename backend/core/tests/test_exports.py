"""« Télécharger » on every screen: PDF, CSV, Excel with the screen's rights (Nov. 2026)."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Membership, User
from core.tenant import tenant_context
from crm.models import Client
from finance.defaults import ensure_expense_categories
from organizations.models import Organization
from staff.models import StaffMember
from stock import services as stock_services
from stock.defaults import ensure_item_categories
from stock.models import ItemCategory

Role = Membership.Role
KINDS = [
    "reservations",
    "clients",
    "quotes",
    "items",
    "movements",
    "invoices",
    "revenues",
    "expenses",
    "staff",
    "tasks",
    "calendar",
]


@pytest.fixture(autouse=True)
def _data(org_a: Organization, owner_a: User) -> None:
    with tenant_context(org_a):
        ensure_item_categories()
        ensure_expense_categories()
        Client.objects.create(name="Famille Ekotto", phone="+237 699 11 22 33")
        stock_services.create_item(
            {
                "name": "Verre à pied",
                "category": ItemCategory.objects.get(name="Vaisselle"),
                "rent_price": 300,
                "purchase_cost": 900,
                "initial_quantity": 500,
            },
            user=owner_a,
        )
        StaffMember.objects.create(
            full_name="Brice Ndzana", position="Installateur", pay_mode="daily", pay_rate=8000
        )


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("output", ["pdf", "csv", "xlsx"])
def test_every_screen_downloads_in_every_format(
    client_for: Callable[..., APIClient],
    org_a: Organization,
    owner_a: User,
    kind: str,
    output: str,
) -> None:
    response = client_for(owner_a, org_a).get(reverse("export", args=[kind]), {"output": output})
    assert response.status_code == 200, response.content[:300]
    head = {"pdf": b"%PDF", "csv": b"\xef\xbb\xbf", "xlsx": b"PK"}[output]
    assert response.content.startswith(head)
    assert f".{output}" in response["Content-Disposition"]


def test_amounts_follow_the_roles_and_spaces_stay_apart(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    org_b: Organization,
    owner_a: User,
    owner_b: User,
) -> None:
    owner = client_for(owner_a, org_a)
    csv = owner.get(reverse("export", args=["items"]), {"output": "csv"}).content.decode()
    assert "Location;Coût d’achat" in csv and "Verre à pied" in csv

    storekeeper = client_for(make_member(org_a, Role.STOREKEEPER), org_a)
    csv = storekeeper.get(reverse("export", args=["items"]), {"output": "csv"}).content.decode()
    assert "Verre à pied" in csv and "Location" not in csv and "Coût" not in csv
    assert storekeeper.get(reverse("export", args=["invoices"])).status_code == 403

    planner = client_for(make_member(org_a, Role.PLANNER), org_a)
    csv = planner.get(reverse("export", args=["staff"]), {"output": "csv"}).content.decode()
    assert "Brice Ndzana" in csv and "Taux" not in csv
    assert planner.get(reverse("export", args=["expenses"])).status_code == 403

    assistant = client_for(make_member(org_a, Role.ASSISTANT), org_a)
    csv = assistant.get(reverse("export", args=["clients"]), {"output": "csv"}).content.decode()
    assert "Famille Ekotto" in csv and "Solde dû" not in csv

    other = client_for(owner_b, org_b)
    csv = other.get(reverse("export", args=["clients"]), {"output": "csv"}).content.decode()
    assert "Ekotto" not in csv
    assert other.get(reverse("export", args=["nope"])).status_code == 404


def test_reports_download_in_csv_too(
    client_for: Callable[..., APIClient], org_a: Organization, owner_a: User
) -> None:
    response = client_for(owner_a, org_a).get(
        reverse("report", args=["expenses"]), {"period": "year", "output": "csv"}
    )
    assert response.status_code == 200
    assert response.content.decode().lstrip("﻿").startswith("Catégorie;Dépensé")
