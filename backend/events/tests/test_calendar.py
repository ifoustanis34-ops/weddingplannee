"""Centralized calendar and drag to move (docs/specs/reservations-stock.md §4.3)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, time, timedelta
from typing import Any

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Membership, User
from core.tenant import tenant_context
from crm.models import Client
from events.models import Wedding
from finance.defaults import ensure_expense_categories
from organizations.models import Organization
from reservations import services
from reservations.models import Reservation
from stock import services as stock_services
from stock.defaults import ensure_item_categories
from stock.models import Item, ItemCategory

Status = Reservation.Status
URL = reverse("calendar")


@pytest.fixture(autouse=True)
def _defaults(org_a: Organization, org_b: Organization) -> None:
    for organization in (org_a, org_b):
        with tenant_context(organization):
            ensure_item_categories()
            ensure_expense_categories()


def at(days: int, hour: int = 10) -> datetime:
    return timezone.make_aware(
        datetime.combine(timezone.localdate() + timedelta(days=days), time(hour))
    )


def day(days: int) -> str:
    return (timezone.localdate() + timedelta(days=days)).isoformat()


def chairs(org: Organization, user: User, quantity: int = 100) -> Item:
    with tenant_context(org):
        item = stock_services.create_item(
            {
                "name": "Chaise Napoléon",
                "category": ItemCategory.objects.get(name="Mobilier"),
                "rent_price": 2000,
                "initial_quantity": quantity,
            },
            user=user,
        )
        item.refresh_from_db()
    return item


def reserve(
    org: Organization, user: User, item: Item, quantity: int, start: int, **extra: Any
) -> Reservation:
    confirm = extra.pop("confirm", True)
    with tenant_context(org):
        client = Client.objects.create(name=extra.pop("client_name", f"Client {start}"))
        reservation = services.create_reservation(
            {
                "client": client,
                "title": "Mariage Awa & Koffi",
                "delivery_at": at(start - 1, 9),
                "setup_at": at(start - 1, 14),
                "event_start": at(start, 15),
                "event_end": at(start, 23),
                "pickup_at": at(start + 1, 10),
                "return_at": at(start + 1, 15),
                "vehicle": "Camion 3,5 t",
                **extra,
            },
            [services.LineInput(kind="rental", item=item, quantity=quantity)],
            user=user,
        )
        if confirm:
            services.confirm(reservation, user=user)
            reservation.refresh_from_db()
    return reservation


def test_one_feed_with_steps_times_and_colors_order(
    client_for: Callable[..., APIClient], org_a: Organization, owner_a: User
) -> None:
    item = chairs(org_a, owner_a)
    reservation = reserve(org_a, owner_a, item, 40, 5)
    with tenant_context(org_a):
        # Its wedding record is not shown twice: the reservation's event stands for it.
        wedding = Wedding.objects.create(
            title="Awa & Koffi", date=timezone.localdate() + timedelta(5)
        )
        reservation.wedding = wedding
        reservation.save()
        Wedding.objects.create(title="Mariam & Idriss", date=timezone.localdate() + timedelta(6))
        stock_services.start_maintenance(
            item,
            reason="Pieds à resserrer",
            user=owner_a,
            expected_end=timezone.localdate() + timedelta(2),
        )

    items = client_for(owner_a, org_a).get(URL, {"from": day(0), "to": day(10)}).json()

    steps = [(i["date"], i["time"], i["kind"]) for i in items if i["reservation"]]
    assert steps == [
        (day(4), "09:00", "delivery"),
        (day(4), "14:00", "setup"),
        (day(5), "15:00", "event"),
        (day(5), None, "payment"),  # balance expected by the event
        (day(6), "10:00", "pickup"),
        (day(6), "15:00", "return"),
    ]
    event = next(i for i in items if i["kind"] == "event" and i["reservation"])
    assert event["vehicle"] == "Camion 3,5 t"
    assert event["movable"] is True
    assert event["owner"] == owner_a.full_name
    assert [i["title"] for i in items if i["kind"] == "event" and not i["reservation"]] == [
        "Mariam & Idriss"
    ]
    maintenance = next(i for i in items if i["kind"] == "maintenance")
    assert (maintenance["date"], maintenance["end_date"]) == (day(0), day(2))


def test_filters_by_member_kind_and_status(
    client_for: Callable[..., APIClient], org_a: Organization, owner_a: User
) -> None:
    item = chairs(org_a, owner_a)
    reserve(org_a, owner_a, item, 10, 5)
    reserve(org_a, owner_a, item, 10, 8, confirm=False)  # draft
    client = client_for(owner_a, org_a)

    deliveries = client.get(URL, {"from": day(0), "to": day(10), "kinds": "delivery"}).json()
    assert [i["date"] for i in deliveries] == [day(4), day(7)]

    drafts = client.get(URL, {"from": day(0), "to": day(10), "statuses": "draft"}).json()
    assert {i["status"] for i in drafts} == {"draft"}
    assert {i["kind"] for i in drafts} == {"delivery", "setup", "event", "pickup", "return"}

    other = client.get(
        URL, {"from": day(0), "to": day(10), "member": str(User.objects.create(email="x@y.ci").pk)}
    ).json()
    assert other == []  # no reservation, no task: maintenance and money belong to no one

    assert client.get(URL, {"from": day(0), "to": day(10), "kinds": "party"}).status_code == 400


def test_roles_money_and_field_roles(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
) -> None:
    item = chairs(org_a, owner_a)
    reserve(org_a, owner_a, item, 10, 5)
    params = {"from": day(0), "to": day(10)}

    storekeeper = client_for(make_member(org_a, Membership.Role.STOREKEEPER), org_a)
    items = storekeeper.get(URL, params).json()
    assert {i["kind"] for i in items} >= {"delivery", "return"}
    assert all(i["kind"] != "payment" and i["amount"] is None for i in items)
    assert all(i["movable"] is False for i in items)

    assistant = client_for(make_member(org_a, Membership.Role.ASSISTANT), org_a)
    assert all(i["kind"] != "payment" for i in assistant.get(URL, params).json())

    lead = client_for(make_member(org_a, Membership.Role.TEAM_LEAD), org_a)
    assert lead.get(URL, params).status_code == 403


def test_drag_moves_every_date_and_checks_the_stock_again(
    client_for: Callable[..., APIClient], org_a: Organization, owner_a: User
) -> None:
    item = chairs(org_a, owner_a, 50)
    moving = reserve(org_a, owner_a, item, 40, 5)
    reserve(org_a, owner_a, item, 30, 12)
    client = client_for(owner_a, org_a)
    url = reverse("reservation-move", args=[moving.pk])

    moved = client.post(url, {"days": 2}, format="json")
    assert moved.status_code == 200
    body = moved.json()
    assert body["delivery_at"].startswith(day(6))
    assert body["return_at"].startswith(day(8))
    assert any("Déplacée" in log["message"] for log in body["logs"])

    # Onto the other wedding: 40 + 30 chairs for 50 owned — refused, nothing changed.
    clash = client.post(url, {"days": 5}, format="json")
    assert clash.status_code == 400
    assert clash.json()["code"] == "stock_insufficient"
    with tenant_context(org_a):
        moving.refresh_from_db()
        assert timezone.localtime(moving.event_start).date().isoformat() == day(7)

    past = client.post(url, {"days": -30}, format="json")
    assert past.status_code == 400


def test_moving_is_for_owner_and_planner_and_stays_in_the_space(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    org_b: Organization,
    owner_a: User,
    owner_b: User,
) -> None:
    item = chairs(org_a, owner_a)
    reservation = reserve(org_a, owner_a, item, 10, 5)
    url = reverse("reservation-move", args=[reservation.pk])

    storekeeper = client_for(make_member(org_a, Membership.Role.STOREKEEPER), org_a)
    assert storekeeper.post(url, {"days": 1}, format="json").status_code == 403
    assert client_for(owner_b, org_b).post(url, {"days": 1}, format="json").status_code == 404
    other_side = client_for(owner_b, org_b).get(URL, {"from": day(0), "to": day(10)}).json()
    assert other_side == []

    with tenant_context(org_a):
        services.checkout(reservation, None, user=owner_a)
    locked = client_for(owner_a, org_a).post(url, {"days": 1}, format="json")
    assert locked.status_code == 400
    assert locked.json()["code"] == "reservation_locked"
