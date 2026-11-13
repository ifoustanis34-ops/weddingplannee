from __future__ import annotations

from django.db.models import QuerySet

from accounts.models import Membership

from .models import Organization


def members_of(organization: Organization) -> QuerySet[Membership]:
    return (
        Membership.objects.filter(organization=organization)
        .select_related("user")
        .order_by("user__full_name")
    )
