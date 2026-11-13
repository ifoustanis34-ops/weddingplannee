from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.tenant import require_current_organization

from .models import DocumentSequence

PREFIXES = {
    DocumentSequence.Kind.CONTRACT: "CT",
    DocumentSequence.Kind.RECEIPT: "RC",
    DocumentSequence.Kind.RESERVATION: "RES",
    DocumentSequence.Kind.INVOICE: "FA",
    DocumentSequence.Kind.CREDIT_NOTE: "AV",
}


def next_number(kind: str, *, year: int | None = None) -> str:
    """Reserve the next document number of the active organization, e.g. ``DV-2026-0048``.

    Quotes use the organization's own prefix (settings, default ``DV``).
    """
    organization = require_current_organization()
    year = year or timezone.localdate().year
    with transaction.atomic():
        try:
            with transaction.atomic():
                DocumentSequence.objects.get_or_create(
                    organization=organization, kind=kind, year=year
                )
        except IntegrityError:  # created concurrently by another request: fine
            pass
        sequence = DocumentSequence.objects.select_for_update().get(
            organization=organization, kind=kind, year=year
        )
        sequence.last_number += 1
        sequence.save(update_fields=["last_number"])
    prefix = (
        organization.quote_prefix
        if kind == DocumentSequence.Kind.QUOTE
        else PREFIXES[DocumentSequence.Kind(kind)]
    )
    return f"{prefix}-{year}-{sequence.last_number:04d}"
