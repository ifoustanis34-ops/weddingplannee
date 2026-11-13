"""The « Mariages » module (feedback 13/11/2026): off by default, on at signup or in settings."""

from __future__ import annotations

from collections.abc import Callable

from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from organizations.models import Organization


def test_wedding_screens_are_refused_while_the_module_is_off(
    client_for: Callable[..., APIClient], owner_a: User, org_a: Organization
) -> None:
    Organization.objects.filter(pk=org_a.pk).update(weddings_enabled=False)
    org_a.refresh_from_db()
    client = client_for(owner_a, org_a)

    assert client.get(reverse("wedding-list")).status_code == 403
    session = client.get(reverse("auth-me")).json()
    assert session["organizations"][0]["weddings_enabled"] is False

    # The owner turns it on in Paramètres › Entreprise.
    assert client.patch(reverse("organization"), {"weddings_enabled": True}).status_code == 200
    assert client.get(reverse("wedding-list")).status_code == 200
    assert client.get(reverse("auth-me")).json()["organizations"][0]["weddings_enabled"] is True


def test_a_new_space_starts_without_weddings_unless_asked(db: None) -> None:
    from organizations import services

    plain = services.create_organization(
        name="Loc Pro", slug="loc-pro", city="Douala", country="CM"
    )
    planner = services.create_organization(
        name="Wed Pro", slug="wed-pro", city="Douala", country="CM", weddings_enabled=True
    )
    assert plain.weddings_enabled is False and planner.weddings_enabled is True
