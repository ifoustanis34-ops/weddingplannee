"""Inbox and app badge (feedback 17/11/2026): every event of the flow, unread count, read."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any
from unittest import mock

from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Membership, User
from core.tenant import tenant_context
from notifications.models import Notification, PushSubscription
from organizations.models import Organization
from staff import services as staff_services
from staff.models import StaffTask
from staff.tests.test_staff import _defaults, person, reservation  # noqa: F401

Role = Membership.Role


def titles(user: User, org: Organization) -> list[str]:
    with tenant_context(org):
        return list(Notification.objects.filter(user=user).values_list("title", flat=True))


def test_the_inbox_fills_even_without_push_keys_and_reads(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
    settings: Any,
) -> None:
    settings.VAPID_PUBLIC_KEY = settings.VAPID_PRIVATE_KEY = ""
    account = make_member(org_a, Role.STAFF)
    linda = person(org_a, "Linda Abena", user=account)
    booked = reservation(org_a, owner_a, 3)
    with tenant_context(org_a):
        staff_services.assign(booked, linda, step="event", role="Service", user=owner_a)
        task = StaffTask.objects.create(staff=linda, reservation=booked, title="Dresser")
        staff_services.mark_done(task, user=account)
        staff_services.validate_task(task, user=owner_a)

    client = client_for(account, org_a)
    body = client.get(reverse("notifications")).json()
    assert [r["title"] for r in body["results"]] == ["Tâche validée", "Nouvelle mission"]
    assert body["unread"] == 2 and body["unread_all"] == 2

    first = body["results"][0]["id"]
    assert client.post(reverse("notification-read", args=[first])).status_code == 204
    assert client.get(reverse("notifications")).json()["unread"] == 1
    assert client.post(reverse("notifications-read-all")).status_code == 204
    assert client.get(reverse("notifications")).json()["unread"] == 0
    # The owner validated the task: they are not told about their own action.
    assert "Tâche validée" not in titles(owner_a, org_a)


def test_reservation_steps_and_attendance_reach_the_managers_not_the_actor(
    make_member: Callable[..., User], org_a: Organization, owner_a: User
) -> None:
    planner = make_member(org_a, Role.PLANNER)
    storekeeper = make_member(org_a, Role.STOREKEEPER)
    booked = reservation(org_a, owner_a, 0)  # created and confirmed by the owner
    assert "Nouvelle réservation" in titles(planner, org_a)
    assert any(t.startswith("Réservation") for t in titles(storekeeper, org_a))
    assert titles(owner_a, org_a) == []  # their own actions

    brice = person(org_a, "Brice Ndzana")
    with tenant_context(org_a):
        mission, _ = staff_services.assign(booked, brice, step="event", role="", user=owner_a)
        staff_services.check_in(mission, user=owner_a, at=mission.start + timedelta(hours=1))
    assert "Arrivée en retard" in titles(planner, org_a)


def test_the_push_carries_each_person_unread_count_for_the_app_icon(
    org_a: Organization, owner_a: User, settings: Any
) -> None:
    from notifications.tasks import deliver

    settings.VAPID_PUBLIC_KEY, settings.VAPID_PRIVATE_KEY = "BPublic", "private"
    PushSubscription.objects.create(
        user=owner_a, endpoint="https://push.example/1", p256dh="k", auth="a"
    )
    with tenant_context(org_a):
        for n in range(3):
            Notification.objects.create(user=owner_a, title=f"Message {n}")
    with mock.patch("pywebpush.webpush") as sent:
        assert deliver([str(owner_a.pk)], {"title": "x"}) == 1
    import json

    assert json.loads(sent.call_args.kwargs["data"])["badge"] == 3


def test_a_person_never_reads_another_space_or_another_person_inbox(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    org_b: Organization,
    owner_a: User,
) -> None:
    other = make_member(org_a, Role.PLANNER)
    with tenant_context(org_a):
        mine = Notification.objects.create(user=owner_a, title="Pour la propriétaire")
    assert client_for(other, org_a).get(reverse("notifications")).json()["results"] == []
    client_for(other, org_a).post(reverse("notification-read", args=[mine.pk]))
    with tenant_context(org_a):
        mine.refresh_from_db()
    assert mine.read_at is None
    owner_b = make_member(org_b, Role.OWNER)
    assert client_for(owner_b, org_b).get(reverse("notifications")).json()["results"] == []
