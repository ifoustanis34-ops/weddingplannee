"""Team settings (CLAUDE.md §7.9, complement §15): invitations, roles, offer, space address."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Membership, TeamInvitation, User
from organizations.models import Organization
from tests.factories import UserFactory

INVITE = reverse("organization-invitations")


@pytest.fixture
def owner_client(
    client_for: Callable[..., APIClient], owner_a: User, org_a: Organization
) -> APIClient:
    return client_for(owner_a, org_a)


def invite(
    client: APIClient, captured: Any, email: str = "awa@maison.ci", role: str = "planner"
) -> Any:
    with captured(execute=True):
        return client.post(INVITE, {"email": email, "role": role}, format="json")


def emailed_token() -> str:
    match = re.search(r"/invitation/([\w-]+)", str(mail.outbox[-1].body))
    assert match, mail.outbox[-1].body
    return match.group(1)


def test_owner_invites_a_member_who_joins_with_a_new_account(
    owner_client: APIClient,
    org_a: Organization,
    django_capture_on_commit_callbacks: Any,
) -> None:
    response = invite(owner_client, django_capture_on_commit_callbacks)
    assert response.status_code == 201, response.json()
    assert mail.outbox[-1].to == ["awa@maison.ci"]
    token = emailed_token()
    # Only a hash of the token is stored.
    assert not TeamInvitation.objects.filter(token_hash=token).exists()

    visitor = APIClient()
    preview = visitor.get(reverse("auth-invitation", args=[token])).json()
    assert (preview["organization_name"], preview["role_label"], preview["has_account"]) == (
        "Agence A",
        "Wedding planner",
        False,
    )

    accepted = visitor.post(
        reverse("auth-invitation-accept", args=[token]),
        {"full_name": "Awa Sangaré", "password": "Mariage-2026!"},
        format="json",
    )
    assert accepted.status_code == 200, accepted.json()
    assert accepted.cookies.get("wedivo_access")
    membership = Membership.objects.get(organization=org_a, user__email="awa@maison.ci")
    assert (membership.role, membership.is_active) == ("planner", True)
    assert User.objects.get(email="awa@maison.ci").is_verified
    # The link works once.
    again = visitor.post(
        reverse("auth-invitation-accept", args=[token]), {"password": "x"}, format="json"
    )
    assert again.status_code == 404


def test_an_existing_account_proves_itself_with_its_password(
    owner_client: APIClient, org_a: Organization, django_capture_on_commit_callbacks: Any
) -> None:
    UserFactory.create(email="didier@maison.ci", password="Ancien-mot-2026")
    invite(owner_client, django_capture_on_commit_callbacks, "didier@maison.ci", "assistant")
    token = emailed_token()
    url = reverse("auth-invitation-accept", args=[token])

    assert APIClient().get(reverse("auth-invitation", args=[token])).json()["has_account"]
    assert APIClient().post(url, {"password": "mauvais"}, format="json").status_code == 401
    assert APIClient().post(url, {"password": "Ancien-mot-2026"}, format="json").status_code == 200
    assert Membership.objects.get(organization=org_a, user__email="didier@maison.ci").role == (
        "assistant"
    )


def test_the_offer_limits_the_number_of_users(
    owner_client: APIClient,
    org_a: Organization,
    django_capture_on_commit_callbacks: Any,
    settings: Any,
) -> None:
    settings.ALL_FEATURES_INCLUDED = False  # the limit only applies when offers are enforced
    Organization.objects.filter(pk=org_a.pk).update(plan="essentiel")  # 1 user

    response = invite(owner_client, django_capture_on_commit_callbacks)

    assert response.status_code == 400
    assert response.json()["code"] == "plan_limit"
    assert "Essentiel" in response.json()["message"]


def test_cannot_invite_an_active_member_or_the_owner_role(
    owner_client: APIClient, owner_a: User, django_capture_on_commit_callbacks: Any
) -> None:
    assert invite(owner_client, django_capture_on_commit_callbacks, owner_a.email).json()[
        "code"
    ] == ("already_member")
    assert (
        invite(owner_client, django_capture_on_commit_callbacks, "x@y.ci", "owner").status_code
        == 400
    )


def test_only_the_owner_manages_the_team(
    client_for: Callable[..., APIClient],
    org_a: Organization,
    make_member: Callable[..., User],
) -> None:
    planner = client_for(make_member(org_a, Membership.Role.PLANNER), org_a)

    assert planner.post(INVITE, {"email": "a@b.ci", "role": "assistant"}).status_code == 403
    assert planner.get(INVITE).status_code == 403
    assert planner.get(reverse("organization-members")).status_code == 200


def test_owner_changes_a_role_and_deactivates_a_member(
    owner_client: APIClient,
    org_a: Organization,
    owner_a: User,
    make_member: Callable[..., User],
) -> None:
    user = make_member(org_a, Membership.Role.ASSISTANT)
    membership = Membership.objects.get(user=user, organization=org_a)
    url = reverse("organization-member", args=[membership.pk])

    assert owner_client.patch(url, {"role": "accountant"}, format="json").json()["role"] == (
        "accountant"
    )
    assert owner_client.patch(url, {"is_active": False}, format="json").json()["is_active"] is False
    owner_membership = Membership.objects.get(user=owner_a, organization=org_a)
    locked = owner_client.patch(
        reverse("organization-member", args=[owner_membership.pk]),
        {"role": "planner"},
        format="json",
    )
    assert locked.status_code == 403
    assert owner_client.patch(url, {"role": "owner"}, format="json").status_code == 400


def test_team_actions_never_reach_another_organization(
    client_for: Callable[..., APIClient],
    org_a: Organization,
    org_b: Organization,
    owner_b: User,
    make_member: Callable[..., User],
) -> None:
    member_a = Membership.objects.get(
        user=make_member(org_a, Membership.Role.ASSISTANT), organization=org_a
    )
    client_b = client_for(owner_b, org_b)

    response = client_b.patch(
        reverse("organization-member", args=[member_a.pk]), {"is_active": False}, format="json"
    )
    assert response.status_code == 404
    assert Membership.objects.get(pk=member_a.pk).is_active


def test_a_cancelled_invitation_link_stops_working(
    owner_client: APIClient, django_capture_on_commit_callbacks: Any
) -> None:
    invitation = invite(owner_client, django_capture_on_commit_callbacks).json()
    token = emailed_token()

    assert owner_client.get(INVITE).json()[0]["email"] == "awa@maison.ci"
    deleted = owner_client.delete(reverse("organization-invitation", args=[invitation["id"]]))
    assert deleted.status_code == 204
    assert APIClient().get(reverse("auth-invitation", args=[token])).status_code == 404
    assert owner_client.get(INVITE).json() == []


def test_the_offer_changes_freely_during_the_trial_only(
    owner_client: APIClient, org_a: Organization
) -> None:
    url = reverse("organization-plan")

    assert owner_client.post(url, {"plan": "agence"}, format="json").json()["plan"] == "agence"
    Organization.objects.filter(pk=org_a.pk).update(trial_ends_at=timezone.now() - timedelta(1))
    after = owner_client.post(url, {"plan": "essentiel"}, format="json")
    assert after.status_code == 400
    assert after.json()["code"] == "plan_change_unavailable"


def test_the_space_address_can_change_with_the_signup_rules(
    owner_client: APIClient, org_a: Organization, org_b: Organization
) -> None:
    url = reverse("organization")

    assert owner_client.patch(url, {"slug": "agence-b"}, format="json").status_code == 400
    assert owner_client.patch(url, {"slug": "admin"}, format="json").status_code == 400
    assert owner_client.patch(url, {"slug": "maison-a"}, format="json").json()["slug"] == (
        "maison-a"
    )
    org_a.refresh_from_db()
    assert org_a.slug == "maison-a"


def test_every_agency_has_every_feature_by_default(
    owner_client: APIClient, org_a: Organization, django_capture_on_commit_callbacks: Any
) -> None:
    """Product decision: whatever its offer, an agency invites as many members as it needs."""
    Organization.objects.filter(pk=org_a.pk).update(plan="essentiel")  # 1 user on paper

    response = invite(owner_client, django_capture_on_commit_callbacks)

    assert response.status_code == 201
