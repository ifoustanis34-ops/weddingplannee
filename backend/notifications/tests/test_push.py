"""Web Push (feedback 13/11/2026): devices, configuration, and who is notified of what."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest import mock

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Membership, User
from core.tenant import tenant_context
from notifications.models import PushSubscription
from organizations.models import Organization
from staff import services
from staff.models import StaffTask
from staff.tests.test_staff import _defaults, person, reservation  # noqa: F401

Role = Membership.Role
ENDPOINT = "https://fcm.googleapis.com/fcm/send/abc123"
DEVICE: dict[str, Any] = {
    "endpoint": ENDPOINT,
    "keys": {"p256dh": "BOrK3y", "auth": "s3cr3t"},
}


@pytest.fixture
def keys(settings: Any) -> None:
    settings.VAPID_PUBLIC_KEY = "BPublicKey"
    settings.VAPID_PRIVATE_KEY = "private"


def test_config_says_disabled_without_keys(
    client_for: Callable[..., APIClient], owner_a: User, org_a: Organization, settings: Any
) -> None:
    settings.VAPID_PUBLIC_KEY = settings.VAPID_PRIVATE_KEY = ""
    body = client_for(owner_a, org_a).get(reverse("push-config")).json()
    assert body == {"enabled": False, "public_key": ""}


def test_a_device_subscribes_moves_to_another_account_and_leaves(
    client_for: Callable[..., APIClient],
    owner_a: User,
    org_a: Organization,
    make_member: Callable[..., User],
    keys: None,
) -> None:
    client = client_for(owner_a, org_a)
    assert client.post(reverse("push-subscriptions"), DEVICE, format="json").status_code == 201
    assert PushSubscription.objects.get().user == owner_a

    other = make_member(org_a, Role.STAFF)  # the same phone, another account
    client_for(other, org_a).post(reverse("push-subscriptions"), DEVICE, format="json")
    assert PushSubscription.objects.get().user == other

    # Someone else cannot remove it; its owner can.
    client.post(reverse("push-subscriptions-remove"), {"endpoint": DEVICE["endpoint"]})
    assert PushSubscription.objects.count() == 1
    client_for(other, org_a).post(
        reverse("push-subscriptions-remove"), {"endpoint": DEVICE["endpoint"]}
    )
    assert PushSubscription.objects.count() == 0


def test_a_gone_device_is_forgotten(owner_a: User, keys: None) -> None:
    from pywebpush import WebPushException

    from notifications.tasks import deliver

    PushSubscription.objects.create(user=owner_a, endpoint=ENDPOINT, p256dh="k", auth="a")
    gone = WebPushException("gone", response=mock.Mock(status_code=410))
    with mock.patch("pywebpush.webpush", side_effect=gone):
        assert deliver([str(owner_a.pk)], {"title": "x"}) == 0
    assert not PushSubscription.objects.exists()

    PushSubscription.objects.create(user=owner_a, endpoint=ENDPOINT, p256dh="k", auth="a")
    with mock.patch("pywebpush.webpush") as sent:
        assert deliver([str(owner_a.pk)], {"title": "x"}) == 1
    assert sent.call_args.kwargs["subscription_info"]["keys"] == {"p256dh": "k", "auth": "a"}


def test_missions_and_tasks_reach_the_right_people(
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
    keys: None,
    django_capture_on_commit_callbacks: Any,
) -> None:
    booked = reservation(org_a, owner_a, 3)
    account = make_member(org_a, Role.STAFF)
    planner = make_member(org_a, Role.PLANNER)
    linda = person(org_a, "Linda Abena", user=account)
    with mock.patch("notifications.tasks.send_push.delay") as delay:
        with tenant_context(org_a), django_capture_on_commit_callbacks(execute=True):
            services.assign(booked, linda, step="event", role="Service", user=owner_a)
        users, payload = delay.call_args.args
        assert users == [str(account.pk)]
        assert payload["title"] == f"{org_a.name} · Nouvelle mission"
        assert payload["url"] == "/mes-missions" and payload["kind"] == "mission"

        with tenant_context(org_a), django_capture_on_commit_callbacks(execute=True):
            task = StaffTask.objects.create(staff=linda, reservation=booked, title="Dresser")
            services.mark_done(task, user=account)
        users, payload = delay.call_args.args
        assert sorted(users) == sorted([str(owner_a.pk), str(planner.pk)])
        assert payload["title"].endswith("Tâche faite, à valider")

        with tenant_context(org_a), django_capture_on_commit_callbacks(execute=True):
            services.reopen(task, user=owner_a, reason="Il manque les verres")
        users, payload = delay.call_args.args
        assert users == [str(account.pk)] and "Il manque les verres" in payload["body"]


def test_nothing_is_queued_without_keys(
    org_a: Organization, owner_a: User, settings: Any, django_capture_on_commit_callbacks: Any
) -> None:
    settings.VAPID_PUBLIC_KEY = settings.VAPID_PRIVATE_KEY = ""
    booked = reservation(org_a, owner_a, 3)
    linda = person(org_a, "Linda Abena", user=owner_a)
    with (
        mock.patch("notifications.tasks.send_push.delay") as delay,
        tenant_context(org_a),
        django_capture_on_commit_callbacks(execute=True),
    ):
        services.assign(booked, linda, step="event", role="", user=owner_a)
    delay.assert_not_called()
