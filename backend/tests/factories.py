from __future__ import annotations

from datetime import timedelta
from typing import Any

import factory
from django.utils import timezone

from accounts.models import Membership, User
from organizations.models import Organization

DEFAULT_PASSWORD = "Mariage-2026!"


class OrganizationFactory(factory.django.DjangoModelFactory[Organization]):
    class Meta:
        model = Organization
        django_get_or_create = ("slug",)

    name = factory.Sequence(lambda n: f"Agence {n}")
    slug = factory.Sequence(lambda n: f"agence-{n}")
    city = "Abidjan"
    country = "CI"
    trial_ends_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=14))
    # The wedding screens predate the « Mariages » module: tests run with it on.
    weddings_enabled = True


class UserFactory(factory.django.DjangoModelFactory[User]):
    class Meta:
        model = User
        django_get_or_create = ("email",)
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.ci")
    full_name = factory.Sequence(lambda n: f"Utilisateur {n}")
    is_verified = True

    @factory.post_generation  # type: ignore[untyped-decorator]
    def password(obj: User, create: bool, extracted: str | None, **kwargs: Any) -> None:
        obj.set_password(extracted or DEFAULT_PASSWORD)
        if create:
            obj.save(update_fields=["password"])


class MembershipFactory(factory.django.DjangoModelFactory[Membership]):
    class Meta:
        model = Membership

    user = factory.SubFactory(UserFactory)
    organization = factory.SubFactory(OrganizationFactory)
    role = Membership.Role.OWNER
    joined_at = factory.LazyFunction(timezone.now)
