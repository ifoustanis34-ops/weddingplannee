"""Deleting a person or a contact (feedback 13/11/2026): history kept, lists cleaned."""

from __future__ import annotations

from collections.abc import Callable

from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Membership, User
from core.models import AuditLog
from core.tenant import tenant_context
from organizations.models import Organization
from staff import services
from staff.models import Assignment, StaffMember
from staff.tests.test_staff import _defaults, person, reservation  # noqa: F401
from vendors.models import Vendor, VendorAssignment

Role = Membership.Role


def test_a_person_without_history_is_deleted_for_good(
    client_for: Callable[..., APIClient], org_a: Organization, owner_a: User
) -> None:
    carine = person(org_a, "Carine Essomba")
    response = client_for(owner_a, org_a).delete(reverse("staff-detail", args=[carine.pk]))

    assert response.status_code == 200
    assert response.json()["permanent"] is True
    with tenant_context(org_a):
        assert not StaffMember.objects.filter(pk=carine.pk).exists()
        assert AuditLog.objects.filter(action="staff.deleted").exists()


def test_a_person_with_history_leaves_the_lists_but_keeps_past_missions(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
) -> None:
    past = reservation(org_a, owner_a, 0)
    coming = reservation(org_a, owner_a, 10)
    account = make_member(org_a, Role.STAFF)
    brice = person(org_a, "Brice Ndzana", user=account)
    with tenant_context(org_a):
        done, _ = services.assign(past, brice, step="event", role="", user=owner_a)
        services.check_in(done, user=owner_a)
        services.assign(coming, brice, step="event", role="", user=owner_a)

    client = client_for(owner_a, org_a)
    response = client.delete(reverse("staff-detail", args=[brice.pk]))

    assert response.status_code == 200
    assert response.json() == {
        "permanent": False,
        "removed_assignments": 1,
        "access_closed": True,
    }
    with tenant_context(org_a):
        brice.refresh_from_db()
        assert brice.is_deleted and not brice.is_active
        assert list(Assignment.objects.filter(staff=brice)) == [done]  # the mission done stays
    assert not Membership.objects.get(user=account, organization=org_a).is_active
    names = [p["full_name"] for p in client.get(reverse("staff-list")).json()]
    assert "Brice Ndzana" not in names
    assert client.get(reverse("staff-detail", args=[brice.pk])).status_code == 404


def test_only_owner_and_planner_delete_and_never_across_spaces(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    org_b: Organization,
    owner_a: User,
) -> None:
    carine = person(org_a, "Carine Essomba")
    assistant = make_member(org_a, Role.ASSISTANT)
    assert (
        client_for(assistant, org_a).delete(reverse("staff-detail", args=[carine.pk])).status_code
        == 403
    )
    owner_b = make_member(org_b, Role.OWNER)
    assert (
        client_for(owner_b, org_b).delete(reverse("staff-detail", args=[carine.pk])).status_code
        == 404
    )
    planner = make_member(org_a, Role.PLANNER)
    assert (
        client_for(planner, org_a).delete(reverse("staff-detail", args=[carine.pk])).status_code
        == 200
    )


def test_a_contact_that_worked_leaves_the_book_but_stays_on_the_wedding(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
) -> None:
    client = client_for(owner_a, org_a)
    unused = client.post(reverse("vendor-list"), {"name": "Kribi Films", "category": "dj"}).json()
    used = client.post(reverse("vendor-list"), {"name": "Le Palmier", "category": "venue"}).json()
    wedding = client.post(reverse("wedding-list"), {"title": "Awa & Koffi"}).json()
    client.post(
        reverse("wedding-vendors", args=[wedding["id"]]),
        {"vendor": used["id"], "service": "Salle", "cost": 500_000},
    )
    assistant = make_member(org_a, Role.ASSISTANT)
    assert (
        client_for(assistant, org_a).delete(reverse("vendor-detail", args=[used["id"]])).status_code
        == 403
    )

    assert client.delete(reverse("vendor-detail", args=[unused["id"]])).status_code == 204
    assert client.delete(reverse("vendor-detail", args=[used["id"]])).status_code == 204

    with tenant_context(org_a):
        assert not Vendor.objects.filter(pk=unused["id"]).exists()
        assert Vendor.objects.get(pk=used["id"]).is_deleted
        assert VendorAssignment.objects.filter(vendor_id=used["id"]).exists()
    assert client.get(reverse("vendor-list")).json() == []
    booked = client.get(reverse("wedding-vendors", args=[wedding["id"]])).json()
    assert [b["vendor_name"] for b in booked] == ["Le Palmier"]
    again = client.post(
        reverse("wedding-vendors", args=[wedding["id"]]),
        {"vendor": used["id"], "service": "Salle"},
    )
    assert again.status_code == 400
