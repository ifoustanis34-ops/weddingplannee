"""Own profile, accounts created by the owner, access of a staff member (feedback 13/11/2026)."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Membership, User
from core.tenant import tenant_context
from organizations.models import Organization
from staff.models import StaffMember
from tests.factories import DEFAULT_PASSWORD

pytestmark = pytest.mark.django_db
TEMP = "Accueil-Douala-2026"


def login(email: str, password: str) -> int:
    response = APIClient().post(
        reverse("auth-login"), {"email": email, "password": password}, format="json"
    )
    return response.status_code


def test_a_member_changes_their_own_name_and_phone(
    org_a: Organization, make_member: Callable[..., User], client_for: Callable[..., APIClient]
) -> None:
    user = make_member(org_a, Membership.Role.STAFF)
    response = client_for(user, org_a).patch(
        reverse("auth-me"), {"full_name": "  Linda   Abena ", "phone": "+237 657 84 74 84"}
    )

    assert response.status_code == 200
    assert response.json()["user"]["full_name"] == "Linda Abena"
    user.refresh_from_db()
    assert user.phone == "+237 657 84 74 84"


def test_the_guided_tour_is_offered_until_followed_or_declined(
    org_a: Organization, make_member: Callable[..., User], client_for: Callable[..., APIClient]
) -> None:
    client = client_for(make_member(org_a, Membership.Role.PLANNER), org_a)
    assert client.get(reverse("auth-me")).json()["user"]["tour_done"] is False

    assert client.post(reverse("auth-me-tour")).status_code == 204
    assert client.get(reverse("auth-me")).json()["user"]["tour_done"] is True
    assert client.post(reverse("auth-me-tour")).status_code == 204  # replayed later: harmless
    assert APIClient().post(reverse("auth-me-tour")).status_code in (401, 403)


def test_changing_the_password_asks_for_the_current_one(
    owner_a: User, org_a: Organization, client_for: Callable[..., APIClient]
) -> None:
    client = client_for(owner_a, org_a)
    url = reverse("auth-me-password")

    wrong = client.post(url, {"current_password": "nope", "new_password": TEMP})
    assert wrong.status_code == 400
    assert "current_password" in wrong.json()["fields"]

    assert (
        client.post(url, {"current_password": DEFAULT_PASSWORD, "new_password": TEMP}).status_code
        == 204
    )
    assert login(owner_a.email, TEMP) == 200


def test_a_pasted_temporary_password_ignores_spaces_around_it(
    owner_a: User, org_a: Organization, client_for: Callable[..., APIClient]
) -> None:
    User.objects.filter(pk=owner_a.pk).update(must_change_password=True)
    client = client_for(owner_a, org_a)
    response = client.post(
        reverse("auth-me-password"),
        {"current_password": f" {DEFAULT_PASSWORD} ", "new_password": TEMP},
    )
    assert response.status_code == 204
    owner_a.refresh_from_db()
    assert not owner_a.must_change_password


def test_spaces_still_count_for_a_chosen_password(
    owner_a: User, org_a: Organization, client_for: Callable[..., APIClient]
) -> None:
    client = client_for(owner_a, org_a)
    response = client.post(
        reverse("auth-me-password"),
        {"current_password": f"{DEFAULT_PASSWORD} ", "new_password": TEMP},
    )
    assert response.status_code == 400


def test_the_owner_creates_an_account_that_must_change_its_password(
    owner_a: User, org_a: Organization, client_for: Callable[..., APIClient]
) -> None:
    response = client_for(owner_a, org_a).post(
        reverse("organization-members"),
        {
            "full_name": "Joël Mbarga",
            "email": "Joel.Mbarga@agence-a.ci",
            "phone": "+237 629 08 07 06",
            "role": "storekeeper",
            "password": TEMP,
        },
    )

    assert response.status_code == 201
    assert response.json()["created_account"] is True
    assert response.json()["member"]["role"] == "storekeeper"
    user = User.objects.get(email="joel.mbarga@agence-a.ci")
    assert user.must_change_password and user.is_verified
    assert login("joel.mbarga@agence-a.ci", TEMP) == 200

    # Their own password then clears the flag.
    client = APIClient()
    client.post(reverse("auth-login"), {"email": user.email, "password": TEMP}, format="json")
    client.post(
        reverse("auth-me-password"),
        {"current_password": TEMP, "new_password": "Mon-Propre-Secret-77"},
        format="json",
    )
    user.refresh_from_db()
    assert not user.must_change_password


def test_only_the_owner_creates_accounts(
    org_a: Organization, make_member: Callable[..., User], client_for: Callable[..., APIClient]
) -> None:
    planner = make_member(org_a, Membership.Role.PLANNER)
    response = client_for(planner, org_a).post(
        reverse("organization-members"),
        {"full_name": "X", "email": "x@agence-a.ci", "role": "staff", "password": TEMP},
    )

    assert response.status_code == 403
    assert not User.objects.filter(email="x@agence-a.ci").exists()


def test_an_existing_account_keeps_its_own_password(
    owner_a: User, owner_b: User, org_a: Organization, client_for: Callable[..., APIClient]
) -> None:
    response = client_for(owner_a, org_a).post(
        reverse("organization-members"),
        {"full_name": "B", "email": owner_b.email, "role": "planner", "password": TEMP},
    )

    assert response.status_code == 201
    assert response.json()["created_account"] is False
    assert login(owner_b.email, DEFAULT_PASSWORD) == 200
    assert login(owner_b.email, TEMP) == 401


def test_the_owner_resets_a_member_password_but_not_across_spaces(
    owner_a: User,
    org_a: Organization,
    org_b: Organization,
    make_member: Callable[..., User],
    client_for: Callable[..., APIClient],
) -> None:
    staff = make_member(org_a, Membership.Role.STAFF)
    membership = Membership.objects.get(user=staff, organization=org_a)
    client = client_for(owner_a, org_a)
    url = reverse("organization-member-password", args=[membership.pk])

    assert client.post(url, {"password": TEMP}).status_code == 204
    assert login(staff.email, TEMP) == 200

    other = make_member(org_b, Membership.Role.STAFF)
    other_membership = Membership.objects.get(user=other, organization=org_b)
    response = client.post(
        reverse("organization-member-password", args=[other_membership.pk]), {"password": TEMP}
    )
    assert response.status_code == 404


def test_the_owner_opens_access_for_a_staff_member(
    owner_a: User, org_a: Organization, client_for: Callable[..., APIClient]
) -> None:
    with tenant_context(org_a):
        person = StaffMember.objects.create(
            full_name="Brice Ndzana", position="Installateur", phone="+237 622 12 22 32"
        )

    response = client_for(owner_a, org_a).post(
        reverse("staff-account", args=[person.pk]),
        {"email": "brice@agence-a.ci", "role": "team_lead", "password": TEMP},
    )

    assert response.status_code == 201
    with tenant_context(org_a):
        person.refresh_from_db()
    assert person.user is not None and person.user.full_name == "Brice Ndzana"
    assert Membership.objects.get(user=person.user, organization=org_a).role == "team_lead"
    second = client_for(owner_a, org_a).post(
        reverse("staff-account", args=[person.pk]),
        {"email": "autre@agence-a.ci", "role": "staff", "password": TEMP},
    )
    assert second.status_code == 400
