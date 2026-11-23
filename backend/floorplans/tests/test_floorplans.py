"""« Croquis » (feedback 20/11/2026): plans drawn to scale, isolated per agency."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Membership, User
from organizations.models import Organization

Role = Membership.Role

PLAN: dict[str, Any] = {
    "name": "Salle des fêtes",
    "venue": "Hôtel Akwa, Douala",
    "length": 24,
    "width": 15.5,
    "elements": [
        {"id": "a", "type": "round_table", "x": 3, "y": 3, "w": 1.8, "h": 1.8, "seats": 10},
        {"id": "b", "type": "chair_row", "x": 1, "y": 9, "w": 5, "h": 0.5, "seats": 10},
        {"id": "c", "type": "chair", "x": 8, "y": 9, "w": 0.5, "h": 0.5},
        {"id": "d", "type": "stage", "x": 18, "y": 2, "w": 5, "h": 3, "label": "Estrade"},
    ],
}


def test_owner_draws_a_plan_and_counts_the_seats(
    client_for: Callable[..., APIClient], owner_a: User, org_a: Organization
) -> None:
    client = client_for(owner_a, org_a)

    created = client.post(reverse("floorplan-list"), PLAN, format="json")

    assert created.status_code == 201, created.json()
    body = created.json()
    assert body["chairs"] == 21
    assert body["length"] == 24 and body["width"] == 15.5
    assert body["elements"][3]["label"] == "Estrade"

    moved = [dict(body["elements"][0], x=5.25)]
    updated = client.patch(
        reverse("floorplan-detail", args=[body["id"]]), {"elements": moved}, format="json"
    )
    assert updated.status_code == 200
    assert updated.json()["elements"][0]["x"] == 5.25
    assert updated.json()["chairs"] == 10


def test_unknown_elements_and_sizes_are_refused(
    client_for: Callable[..., APIClient], owner_a: User, org_a: Organization
) -> None:
    client = client_for(owner_a, org_a)

    bad_type = client.post(
        reverse("floorplan-list"), {**PLAN, "elements": [{"type": "piano"}]}, format="json"
    )
    too_small = client.post(reverse("floorplan-list"), {**PLAN, "length": 0}, format="json")

    assert bad_type.status_code == 400
    assert too_small.status_code == 400


def test_storekeeper_reads_but_does_not_draw(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    owner_a: User,
    org_a: Organization,
) -> None:
    plan = client_for(owner_a, org_a).post(reverse("floorplan-list"), PLAN, format="json").json()
    storekeeper = client_for(make_member(org_a, Role.STOREKEEPER), org_a)

    assert storekeeper.get(reverse("floorplan-detail", args=[plan["id"]])).status_code == 200
    assert storekeeper.post(reverse("floorplan-list"), PLAN, format="json").status_code == 403


def test_another_agency_cannot_see_the_plan(
    client_for: Callable[..., APIClient],
    owner_a: User,
    owner_b: User,
    org_a: Organization,
    org_b: Organization,
) -> None:
    plan = client_for(owner_a, org_a).post(reverse("floorplan-list"), PLAN, format="json").json()
    other = client_for(owner_b, org_b)

    assert other.get(reverse("floorplan-list")).json() == []
    assert other.get(reverse("floorplan-detail", args=[plan["id"]])).status_code == 404
    assert other.delete(reverse("floorplan-detail", args=[plan["id"]])).status_code == 404


def test_new_elements_and_the_ambiance_are_kept(
    client_for: Callable[..., APIClient], owner_a: User, org_a: Organization
) -> None:
    client = client_for(owner_a, org_a)
    body = {
        **PLAN,
        "elements": [
            {"id": "h", "type": "head_table", "x": 2, "y": 1, "w": 5, "h": 0.9, "seats": 6},
            {"id": "p", "type": "plant", "x": 1, "y": 1, "w": 0.6, "h": 0.6},
        ],
        "ambiance": {"floor": "parquet", "light": "evening"},
    }

    created = client.post(reverse("floorplan-list"), body, format="json")
    refused = client.post(
        reverse("floorplan-list"), {**body, "ambiance": {"floor": "lava"}}, format="json"
    )

    assert created.status_code == 201, created.json()
    assert created.json()["chairs"] == 6
    assert created.json()["ambiance"] == {
        "floor": "parquet",
        "walls": "white",
        "light": "evening",
        "height": 3.0,
    }
    assert refused.status_code == 400
