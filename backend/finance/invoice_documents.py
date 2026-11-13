"""Invoice and credit note documents (§6.3): the agency's quote templates and palette
(prompt « Devis et billets »), titled « FACTURE » or « AVOIR ». The snapshot is taken at
issue and stored with the document, so a PDF printed later is the same document."""

from __future__ import annotations

from datetime import date
from typing import Any

from django.utils import timezone

from documents import icons, palettes, quote_document, rendering
from documents import services as branding_services
from organizations.timezones import org_tz

from .models import CreditNote, Invoice

TITLES = {"invoice": ("FACTURE", "Facture"), "credit_note": ("AVOIR", "Avoir")}


def _base(
    *,
    kind: str,
    number: str,
    issued: date,
    due: date | None,
    reservation: Any,
    lines: list[dict[str, Any]],
    total: int,
    tagline: str,
    terms: list[str],
) -> dict[str, Any]:
    branding = branding_services.get_branding()
    trade_name = branding.trade_name or branding.organization.name
    template = branding.quote_design or quote_document.DEFAULT_TEMPLATE
    event_day = timezone.localtime(reservation.event_start, org_tz(reservation.organization)).date()
    client = reservation.client
    return {
        "version": quote_document.SNAPSHOT_VERSION,
        "organization_id": str(reservation.organization_id),
        "template": template if template in quote_document.TEMPLATES else "A",
        "palette": palettes.get(branding.quote_palette).code,
        "status": kind,
        "kind": kind,
        "agency": quote_document.agency_snapshot(branding, branding_services.monogram(trade_name)),
        "partners": [],
        "quote": {
            "number": number,
            "issue_date": issued.isoformat(),
            "valid_until": (due or issued).isoformat(),
            "validity_days": max(1, ((due or issued) - issued).days),
            "tagline": tagline,
            "client": {"name": client.name, "phone": client.phone, "email": client.email},
            "event": {
                "type": reservation.title,
                "date": event_day.isoformat(),
                "venue": reservation.venue,
                "guests": reservation.guest_count,
            },
            "lines": [
                {
                    "label": line["label"],
                    "description": "",
                    "icon": icons.guess(line["label"]),
                    "quantity": str(line["quantity"]),
                    "unit": "",
                    "unit_price": line["unit_price"],
                    "amount": line["amount"],
                }
                for line in lines
            ],
            # Deductions (discount, invoiced deposit) are lines of their own: no extra row.
            "subtotal": total,
            "discount_pct": "0",
            "discount_amount": 0,
            "total": total,
            "deposit_pct": "0",
            "deposit_amount": 0,
            "balance": 0,
            "payment_terms": terms,
            # Legal mentions of the agency (Paramètres › Entreprise), one per line.
            "terms": quote_document._lines(reservation.organization.legal_mentions),
        },
        "photos": {"hero": None, "side": None},
    }


def invoice_snapshot(invoice: Invoice) -> dict[str, Any]:
    reservation = invoice.reservation
    lines = [
        {
            "label": line.label,
            "quantity": line.quantity,
            "unit_price": line.unit_price,
            "amount": line.amount,
        }
        for line in invoice.lines.all()
    ]
    label = "Facture d’acompte" if invoice.kind == Invoice.Kind.DEPOSIT else "Facture"
    return _base(
        kind="invoice",
        number=invoice.number,
        issued=invoice.issued_at,
        due=invoice.due_at,
        reservation=reservation,
        lines=lines,
        total=invoice.total,
        tagline=f"{label} · Réservation {reservation.number}",
        terms=[
            f"À régler au plus tard le {quote_document.long_date(invoice.due_at.isoformat())}.",
            f"Merci de rappeler la référence {invoice.number} avec votre paiement.",
            f"Modes acceptés : {METHODS}",
        ],
    )


def credit_note_snapshot(note: CreditNote) -> dict[str, Any]:
    reservation = note.reservation
    return _base(
        kind="credit_note",
        number=note.number,
        issued=note.issued_at,
        due=None,
        reservation=reservation,
        lines=[
            {
                "label": f"Avoir sur la facture {note.invoice.number} — {note.reason}",
                "quantity": 1,
                "unit_price": note.amount,
                "amount": note.amount,
            }
        ],
        total=note.amount,
        tagline=f"Avoir · Facture {note.invoice.number}",
        terms=[
            f"Cet avoir annule {quote_document.money(note.amount)} "
            f"de la facture {note.invoice.number}.",
            "Il est déduit de vos prochains règlements ou remboursé sur demande.",
        ],
    )


METHODS = "espèces, virement, Orange Money, MTN MoMo, Wave ou chèque."


def render_pdf(snapshot: dict[str, Any]) -> bytes:
    """The same templates as the quotes; only the title and the watermark change."""
    title, name = TITLES[snapshot["kind"]]
    context = {
        **quote_document.context(snapshot),
        "doc_label": title,
        "doc_name": name,
        "schedule": [],
        "watermark": "",
    }
    html_template = quote_document.template_path(snapshot)
    return rendering.render(html_template, context, snapshot["organization_id"]).pdf


def filename(number: str) -> str:
    return f"{number}.pdf"
