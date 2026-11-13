"""Quote documents: preview, versioned generation (docs/specs/devis-billets.md §3, §5).

- The editor preview is rendered from the draft data (nothing saved), cached 10 minutes by
  fingerprint of the snapshot.
- « Générer le PDF » and « Envoyer » freeze a GeneratedDocument: the snapshot, the PDF, the
  first-page PNG and the SHA-256 of the PDF. The same data never makes a new version; a
  change always does (a sent document is never regenerated in silence).
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from decimal import Decimal
from typing import Any

from django.core.files.base import ContentFile
from django.db import transaction

from core.tenant import require_current_organization
from quotes.calculations import line_amount
from quotes.models import Quote, QuoteLine, QuotePartner

from . import quote_document, rendering, services
from .models import DocumentTemplate, GeneratedDocument

KIND = DocumentTemplate.Kind.QUOTE


def _snapshot(
    quote: Quote, lines: Iterable[Any], partners: Iterable[Any], client: Any
) -> dict[str, Any]:
    branding = services.get_branding()
    return quote_document.build_snapshot(
        organization_id=str(require_current_organization().pk),
        branding=branding,
        monogram=services.monogram(branding.trade_name or branding.organization.name),
        quote=quote,
        lines=lines,
        partners=partners,
        client=client,
    )


def quote_snapshot(quote: Quote) -> dict[str, Any]:
    return _snapshot(
        quote,
        quote.lines.select_related("service_item").all(),
        quote.partners.all(),
        quote.client,
    )


def draft_snapshot(data: dict[str, Any], base: Quote | None = None) -> dict[str, Any]:
    """The editor's unsaved data (validated by QuoteSerializer) as a snapshot."""
    quote = Quote(
        organization=require_current_organization(),
        number=base.number if base else "",
        status=base.status if base else Quote.Status.DRAFT,
    )
    for field in (
        "client",
        "issue_date",
        "valid_until",
        "wedding_date",
        "guest_count",
        "discount_pct",
        "deposit_pct",
        "payment_terms",
        "design",
        "palette",
        "tagline",
        "event_type",
        "venue",
    ):
        if field in data:
            setattr(quote, field, data[field])
        elif base is not None:
            setattr(quote, field, getattr(base, field))
    if quote.issue_date is None or quote.valid_until is None:
        from quotes.services import default_dates

        quote.issue_date, quote.valid_until = default_dates()
    quote.discount_pct = quote.discount_pct if quote.discount_pct is not None else Decimal(0)
    quote.deposit_pct = quote.deposit_pct if quote.deposit_pct is not None else Decimal(0)
    lines = [
        QuoteLine(
            label=line.get("label", ""),
            description=line.get("description", ""),
            unit=line.get("unit", "flat"),
            unit_price=line.get("unit_price", 0),
            quantity=line.get("quantity", Decimal(1)),
            amount=line_amount(line.get("unit_price", 0), line.get("quantity", Decimal(1))),
            icon=line.get("icon", ""),
            service_item=line.get("service_item"),
        )
        for line in data.get("lines", [])
    ]
    partners = [QuotePartner(**partner) for partner in data.get("partners", [])]
    if "partners" not in data and base is not None:
        partners = list(base.partners.all())
    return _snapshot(quote, lines, partners, quote.client)


def render(snapshot: dict[str, Any]) -> rendering.Rendering:
    return rendering.render(
        quote_document.template_path(snapshot),
        quote_document.context(snapshot),
        snapshot["organization_id"],
    )


def preview(snapshot: dict[str, Any]) -> tuple[bytes, int]:
    return rendering.cached_preview(
        snapshot["organization_id"], KIND, snapshot, lambda: render(snapshot)
    )


def latest(quote: Quote) -> GeneratedDocument | None:
    return (
        GeneratedDocument.objects.filter(kind=KIND, object_id=quote.pk).order_by("-version").first()
    )


@transaction.atomic
def generate(quote: Quote) -> GeneratedDocument:
    """The PDF of the quote as it is now; the last version is reused if nothing changed."""
    snapshot = quote_snapshot(quote)
    fingerprint = rendering.fingerprint(snapshot)
    # Lock the quote: two simultaneous generations must not both create version N + 1.
    Quote.objects.select_for_update().filter(pk=quote.pk).first()
    current = latest(quote)
    if current is not None and rendering.fingerprint(current.data_snapshot) == fingerprint:
        return current
    template = DocumentTemplate.objects.filter(
        kind=KIND, code=snapshot["template"]
    ).first() or DocumentTemplate.objects.get(kind=KIND, code=quote_document.DEFAULT_TEMPLATE)
    result = render(snapshot)
    document = GeneratedDocument(
        # Set now: the file paths (org/{id}/documents/…) are computed before save().
        organization=require_current_organization(),
        kind=KIND,
        object_id=quote.pk,
        version=(current.version + 1) if current else 1,
        template=template,
        data_snapshot=snapshot,
        sha256=hashlib.sha256(result.pdf).hexdigest(),
        page_count=result.page_count,
    )
    document.pdf_file.save(f"{filename(quote)}", ContentFile(result.pdf), save=False)
    document.png_file.save("page-1.png", ContentFile(result.pages[0]), save=False)
    document.save()
    return document


def document_preview(document: GeneratedDocument) -> tuple[bytes, int]:
    """All pages of a frozen version as one PNG (the public page shows what was sent)."""
    from django.core.cache import cache

    key = f"org:{document.organization_id}:document:{document.sha256}:png"
    hit = cache.get(key)
    if hit is None:
        pages = rendering.pdf_to_pngs(pdf_bytes(document))
        hit = {"png": rendering.stack(pages), "pages": len(pages)}
        cache.set(key, hit, rendering.PREVIEW_TTL)
    return hit["png"], hit["pages"]


def pdf_bytes(document: GeneratedDocument) -> bytes:
    with document.pdf_file.open("rb") as handle:
        content: bytes = handle.read()
    return content


def filename(quote: Quote) -> str:
    return f"{quote.number or 'devis'}.pdf"
