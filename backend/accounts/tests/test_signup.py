from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Membership, User
from organizations.models import Organization

pytestmark = pytest.mark.django_db

SIGNUP_URL = reverse("auth-signup")


def payload(**overrides: Any) -> dict[str, Any]:
    data = {
        "company_name": "Maison Élégance Events",
        "city": "Abidjan",
        "country": "ci",
        "weddings_per_year": 40,
        "full_name": "Aïcha Koné",
        "email": "Aicha@Maison-Elegance.ci",
        "phone": "+225 07 08 12 34 56",
        "password": "Mariage-2026!",
        "slug": "maison-elegance",
        "plan": "pro",
    }
    data.update(overrides)
    return data


def test_signup_creates_organization_owner_and_session(
    django_capture_on_commit_callbacks: Any,
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        response = APIClient().post(SIGNUP_URL, payload(), format="json")

    assert response.status_code == 201, response.json()
    organization = Organization.objects.get(slug="maison-elegance")
    user = User.objects.get(email="aicha@maison-elegance.ci")
    membership = Membership.objects.get(user=user, organization=organization)
    assert membership.role == Membership.Role.OWNER
    assert organization.country == "CI"
    assert organization.plan == Organization.Plan.PRO
    assert organization.trial_ends_at is not None
    assert abs(organization.trial_ends_at - (timezone.now() + timedelta(days=14))) < timedelta(
        minutes=1
    )
    body = response.json()
    assert body["user"]["email"] == "aicha@maison-elegance.ci"
    assert body["organizations"][0]["slug"] == "maison-elegance"
    assert response.cookies["wedivo_access"]["httponly"]
    assert response.cookies["wedivo_refresh"]["httponly"]
    assert len(mail.outbox) == 1
    assert "verifier-email?token=" in mail.outbox[0].body


def test_signup_accepts_only_required_fields() -> None:
    data = payload()
    for optional in ("weddings_per_year", "phone", "plan"):
        data.pop(optional)

    response = APIClient().post(SIGNUP_URL, data, format="json")

    assert response.status_code == 201, response.json()
    organization = Organization.objects.get(slug="maison-elegance")
    assert organization.weddings_per_year is None
    assert organization.plan == Organization.Plan.PRO


@pytest.mark.parametrize("slug", ["admin", "www", "api", "-bad-", "ab", "mariage_2026"])
def test_signup_refuses_reserved_or_invalid_slug(slug: str) -> None:
    response = APIClient().post(SIGNUP_URL, payload(slug=slug), format="json")

    assert response.status_code == 400
    assert response.json()["code"] == "slug_unavailable"
    assert "slug" in response.json()["fields"]
    assert not Organization.objects.exists()


def test_signup_normalizes_slug_to_lowercase() -> None:
    response = APIClient().post(SIGNUP_URL, payload(slug="Maison-Elegance"), format="json")

    assert response.status_code == 201
    assert Organization.objects.filter(slug="maison-elegance").exists()


def test_signup_refuses_existing_email(owner_a: User) -> None:
    response = APIClient().post(SIGNUP_URL, payload(email=owner_a.email), format="json")

    assert response.status_code == 400
    assert response.json()["code"] == "email_taken"


def test_signup_refuses_weak_password() -> None:
    response = APIClient().post(SIGNUP_URL, payload(password="12345678"), format="json")

    assert response.status_code == 400
    assert "password" in response.json()["fields"]
    assert not User.objects.exists()


def test_signup_reports_missing_fields_per_field() -> None:
    response = APIClient().post(SIGNUP_URL, {"company_name": "X"}, format="json")

    body = response.json()
    assert response.status_code == 400
    assert body["code"] == "invalid"
    assert {"city", "email", "password", "slug"} <= set(body["fields"])


def test_signup_is_atomic(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(Membership.objects, "create", explode)

    with pytest.raises(RuntimeError):
        APIClient().post(SIGNUP_URL, payload(), format="json")

    assert not Organization.objects.exists()
    assert not User.objects.exists()


def test_signup_is_rate_limited_per_ip() -> None:
    client = APIClient()
    for _ in range(5):
        client.post(SIGNUP_URL, payload(slug="admin"), format="json")

    response = client.post(SIGNUP_URL, payload(), format="json")

    assert response.status_code == 429
    assert response.json()["code"] == "rate_limited"


def test_slug_availability_and_suggestion(org_a: Organization) -> None:
    url = reverse("auth-slug-available")
    client = APIClient()

    assert client.get(url, {"slug": "agence-a"}).json()["available"] is False
    assert (
        client.get(url, {"slug": "status"})
        .json()["reason"]
        .startswith("Cette adresse est réservée")
    )
    assert client.get(url, {"slug": "nouvelle-agence"}).json() == {
        "slug": "nouvelle-agence",
        "available": True,
        "reason": None,
    }
    suggestion = client.get(url, {"name": "Agence A"}).json()
    assert suggestion == {"slug": "agence-a-2", "available": True, "reason": None}
