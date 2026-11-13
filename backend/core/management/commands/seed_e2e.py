"""Dedicated space for browser journeys (`make e2e`): keeps the demo agency clean.

Idempotent. The account is verified so journeys can send quotes (CLAUDE.md §11).
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import Membership, User
from organizations import services as organization_services
from organizations.models import Organization

E2E_SLUG = "studio-e2e"
E2E_EMAIL = "e2e@wedivo.test"
E2E_PASSWORD = "Mariage-E2E-2026"


class Command(BaseCommand):
    help = "Create the « Studio E2E » space used by Playwright journeys."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG:
            # A known password must never exist outside development and test environments.
            raise CommandError("seed_e2e ne s’exécute qu’en développement (DJANGO_DEBUG=true).")
        organization = Organization.objects.filter(slug=E2E_SLUG).first()
        if organization is None:
            organization = organization_services.create_organization(
                name="Studio E2E", slug=E2E_SLUG, city="Douala", country="CM"
            )
        # The journeys cover the wedding screens (tickets): the module is on.
        Organization.objects.filter(pk=organization.pk).update(weddings_enabled=True)
        user, created = User.objects.get_or_create(
            email=E2E_EMAIL, defaults={"full_name": "Planner E2E", "is_verified": True}
        )
        if created:
            user.set_password(E2E_PASSWORD)
            user.save(update_fields=["password"])
        Membership.objects.update_or_create(
            user=user,
            organization=organization,
            defaults={
                "role": Membership.Role.OWNER,
                "is_active": True,
                "joined_at": timezone.now(),
            },
        )
        self.stdout.write(self.style.SUCCESS(f"Espace E2E prêt : {E2E_EMAIL}"))
