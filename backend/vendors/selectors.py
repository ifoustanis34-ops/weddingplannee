"""Vendor statistics: collaborations and amount still owed (complement §13)."""

from __future__ import annotations

from typing import Any

from django.db.models import (
    BigIntegerField,
    Count,
    F,
    IntegerField,
    OuterRef,
    QuerySet,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce

from .models import Vendor, VendorAssignment

TOP_DUE = 6


def vendors_with_stats() -> QuerySet[Vendor]:
    assignments = VendorAssignment.objects.filter(vendor=OuterRef("pk")).order_by().values("vendor")
    vendors: QuerySet[Vendor] = Vendor.objects.filter(is_deleted=False).annotate(
        collaborations=Coalesce(
            Subquery(assignments.annotate(n=Count("pk")).values("n"), output_field=IntegerField()),
            Value(0),
        ),
        due=Coalesce(
            Subquery(
                assignments.annotate(total=Sum(F("cost") - F("paid_amount"))).values("total"),
                output_field=BigIntegerField(),
            ),
            Value(0, output_field=BigIntegerField()),
        ),
    )
    return vendors


def amounts_due() -> list[dict[str, Any]]:
    """« À payer aux fournisseurs » (complement §12): biggest amounts still owed."""
    rows = vendors_with_stats().filter(due__gt=0).order_by("-due")[:TOP_DUE]  # type: ignore[misc]
    return [
        {
            "id": str(vendor.pk),
            "name": vendor.name,
            "category_label": vendor.get_category_display(),
            "due": int(vendor.due),  # type: ignore[attr-defined]
        }
        for vendor in rows
    ]
