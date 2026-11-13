from __future__ import annotations

from collections.abc import Callable

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from catalog.models import ServiceCategory
from core.tenant import tenant_context
from organizations.models import Organization

pytestmark = pytest.mark.django_db


def test_signup_creates_a_sample_catalog(django_capture_on_commit_callbacks: object) -> None:
    response = APIClient().post(
        reverse("auth-signup"),
        {
            "company_name": "Doux Moments",
            "city": "Dakar",
            "country": "SN",
            "full_name": "Awa Diop",
            "email": "awa@doux.sn",
            "password": "Mariage-Dakar-2026",
            "slug": "doux-moments",
        },
        format="json",
    )
    assert response.status_code == 201
    organization = Organization.objects.get(slug="doux-moments")
    with tenant_context(organization):
        names = list(ServiceCategory.objects.values_list("name", flat=True))
    assert names[:3] == ["Coordination", "Décoration", "Restauration"]


def test_planner_manages_items_assistant_only_reads(
    client_for: Callable[..., APIClient],
    org_a: Organization,
    make_member: Callable[..., User],
) -> None:
    planner = client_for(make_member(org_a, "planner"), org_a)
    category = planner.post(
        reverse("catalog-categories"), {"name": "Lumières"}, format="json"
    ).json()
    item = planner.post(
        reverse("catalog-items"),
        {
            "category": category["id"],
            "name": "Projecteurs LED",
            "unit": "evening",
            "unit_price": 120_000,
        },
        format="json",
    )
    assert item.status_code == 201
    assert item.json()["unit_label"] == "Soirée"

    assistant = client_for(make_member(org_a, "assistant"), org_a)
    assert (
        assistant.get(reverse("catalog-categories")).json()[0]["items"][0]["name"]
        == "Projecteurs LED"
    )
    assert (
        assistant.post(reverse("catalog-categories"), {"name": "X"}, format="json").status_code
        == 403
    )


def test_items_cannot_use_another_organization_category(
    client_for: Callable[..., APIClient],
    owner_a: User,
    org_a: Organization,
    owner_b: User,
    org_b: Organization,
) -> None:
    category = (
        client_for(owner_a, org_a)
        .post(reverse("catalog-categories"), {"name": "Privée"}, format="json")
        .json()
    )

    response = client_for(owner_b, org_b).post(
        reverse("catalog-items"),
        {"category": category["id"], "name": "X", "unit_price": 1},
        format="json",
    )

    assert response.status_code == 400
    assert (
        client_for(owner_b, org_b)
        .get(reverse("catalog-category-detail", args=[category["id"]]))
        .status_code
        == 404
    )


def test_non_empty_category_cannot_be_deleted(
    client_for: Callable[..., APIClient], owner_a: User, org_a: Organization
) -> None:
    client = client_for(owner_a, org_a)
    category = client.post(reverse("catalog-categories"), {"name": "Image"}, format="json").json()
    client.post(
        reverse("catalog-items"),
        {"category": category["id"], "name": "Photographe", "unit_price": 1},
        format="json",
    )

    response = client.delete(reverse("catalog-category-detail", args=[category["id"]]))

    assert response.json()["code"] == "category_not_empty"
