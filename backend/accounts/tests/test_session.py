from __future__ import annotations

from collections.abc import Callable

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from organizations.models import Organization
from tests.factories import DEFAULT_PASSWORD

pytestmark = pytest.mark.django_db


def login(client: APIClient, email: str, password: str = DEFAULT_PASSWORD):  # type: ignore[no-untyped-def]
    return client.post(reverse("auth-login"), {"email": email, "password": password}, format="json")


def test_login_sets_httponly_cookies_and_lists_spaces(owner_a: User, org_a: Organization) -> None:
    response = login(APIClient(), "OWNER@agence-a.ci")

    assert response.status_code == 200
    assert response.json()["organizations"] == [
        {
            "organization_id": str(org_a.pk),
            "slug": "agence-a",
            "name": "Agence A",
            "role": "owner",
            "role_label": "Propriétaire",
            "weddings_enabled": True,
        }
    ]
    access = response.cookies["wedivo_access"]
    refresh = response.cookies["wedivo_refresh"]
    assert access["httponly"] and refresh["httponly"]
    assert access["samesite"] == "Lax"
    assert refresh["path"] == "/api/v1/auth/"


def test_login_with_wrong_password_is_refused(owner_a: User) -> None:
    response = login(APIClient(), owner_a.email, "mauvais")

    assert response.status_code == 401
    assert response.json() == {
        "code": "invalid_credentials",
        "message": "Email ou mot de passe incorrect.",
        "fields": {},
    }


def test_login_is_limited_to_five_attempts(owner_a: User) -> None:
    client = APIClient()
    for _ in range(5):
        assert login(client, owner_a.email, "mauvais").status_code == 401

    response = login(client, owner_a.email)

    assert response.status_code == 429
    assert response.json()["code"] == "rate_limited"
    assert "Retry-After" in response


def test_me_returns_the_session(client_for: Callable[..., APIClient], owner_a: User) -> None:
    response = client_for(owner_a).get(reverse("auth-me"))

    assert response.status_code == 200
    assert response.json()["user"]["email"] == owner_a.email


def test_refresh_rotates_and_old_refresh_token_is_revoked(owner_a: User) -> None:
    client = APIClient()
    login(client, owner_a.email)
    old_refresh = client.cookies["wedivo_refresh"].value

    first = client.post(reverse("auth-refresh"))
    assert first.status_code == 204
    assert client.cookies["wedivo_refresh"].value != old_refresh

    replay = APIClient()
    replay.cookies["wedivo_refresh"] = old_refresh
    response = replay.post(reverse("auth-refresh"))
    assert response.status_code == 401
    assert response.json()["code"] == "session_expired"


def test_logout_revokes_refresh_and_clears_cookies(owner_a: User) -> None:
    client = APIClient()
    login(client, owner_a.email)
    refresh = client.cookies["wedivo_refresh"].value

    response = client.post(reverse("auth-logout"))

    assert response.status_code == 204
    assert response.cookies["wedivo_access"].value == ""
    replay = APIClient()
    replay.cookies["wedivo_refresh"] = refresh
    assert replay.post(reverse("auth-refresh")).status_code == 401


def test_cookie_session_requires_csrf_token_on_writes(owner_a: User, org_a: Organization) -> None:
    client = APIClient(enforce_csrf_checks=True)
    login(client, owner_a.email)
    client.credentials(HTTP_X_ORGANIZATION=org_a.slug)

    refused = client.patch(reverse("organization"), {"city": "Bouaké"}, format="json")
    assert refused.status_code == 403
    assert refused.json()["code"] == "csrf_failed"

    client.get(reverse("auth-csrf"))
    token = client.cookies["csrftoken"].value
    accepted = client.patch(
        reverse("organization"), {"city": "Bouaké"}, format="json", HTTP_X_CSRFTOKEN=token
    )
    assert accepted.status_code == 200
