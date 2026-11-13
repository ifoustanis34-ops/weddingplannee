from __future__ import annotations

import factory

from crm.models import Client


class ClientFactory(factory.django.DjangoModelFactory[Client]):
    """Create inside ``tenant_context(org)``: the organization comes from the context."""

    class Meta:
        model = Client

    name = factory.Sequence(lambda n: f"Client {n}")
    phone = factory.Sequence(lambda n: f"+225 07 {n:08d}")
