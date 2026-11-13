"""Quote documents: the frozen data snapshot and the template context (§2b, §2d, §2e, §5).

The snapshot holds raw values only (integers, ISO dates, storage names): it is what a
GeneratedDocument keeps, so that a sent quote can be rendered again identically.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from typing import Any

from catalog.models import Unit
from quotes.calculations import compute_totals

from . import icons, palettes
from .models import OrganizationBranding
from .rendering import asset_url, file_url

SNAPSHOT_VERSION = 1
TEMPLATES = {"A": "Prestige", "B": "Élégance", "C": "Classique", "D": "Partenariat"}
DEFAULT_TEMPLATE = "A"
NNBSP = " "
NBSP = " "
MONTHS = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]
UNIT_LABELS = dict(Unit.choices)
DEFAULT_THANKS = (
    "Nous mettons tout en œuvre pour faire de votre événement un moment unique et inoubliable."
)


# --- Snapshot ------------------------------------------------------------------------------------


def _lines(text: str) -> list[str]:
    return [line.strip(" -•\t") for line in (text or "").splitlines() if line.strip(" -•\t")]


def _quantity(value: Decimal | int | str) -> str:
    return f"{Decimal(value).normalize():f}"


def default_payment_terms(deposit_pct: Decimal, validity_days: int) -> list[str]:
    deposit = _quantity(deposit_pct)
    rest = _quantity(Decimal(100) - Decimal(deposit_pct))
    terms = []
    if Decimal(deposit_pct) > 0:
        terms.append(f"{deposit}{NBSP}% à la signature du devis pour la réservation de la date.")
        terms.append(f"{rest}{NBSP}% au plus tard 7 jours avant l’événement.")
    else:
        terms.append("Règlement au plus tard 7 jours avant l’événement.")
    terms.append(
        "Tout changement après validation du devis peut entraîner une modification des tarifs."
    )
    terms.append(f"Le devis est valable {validity_days} jours à compter de la date d’émission.")
    return terms


def default_quote_terms(validity_days: int) -> list[str]:
    return [
        f"Ce devis est valable pendant {validity_days} jours à compter de la date d’émission.",
        "Les prix sont exprimés en francs CFA (FCFA).",
        "Toute annulation doit être notifiée par écrit au moins 15 jours avant l’événement.",
        "Le solde est à régler au plus tard 7 jours avant la date de l’événement.",
        "Des frais supplémentaires peuvent s’appliquer en cas de modification des prestations.",
    ]


def agency_snapshot(branding: OrganizationBranding, monogram: str) -> dict[str, Any]:
    return {
        "trade_name": branding.trade_name or branding.organization.name,
        "legal_name": branding.legal_name,
        "activity": branding.activity,
        "slogan": branding.slogan,
        "address": branding.address,
        "phones": list(branding.phones),
        "whatsapp": branding.whatsapp,
        "email": branding.email,
        "website": branding.website,
        "socials": dict(branding.socials),
        "tax_ids": dict(branding.tax_ids),
        "vat_rate": str(branding.vat_rate) if branding.vat_rate is not None else None,
        "bank_details": branding.bank_details,
        "mobile_money_numbers": list(branding.mobile_money_numbers),
        "activities": list(branding.activities),
        "engagements": list(branding.engagements),
        "quote_tagline": branding.quote_tagline,
        "scripts": dict(branding.scripts),
        "signatory": branding.signatory,
        "signatory_role": branding.signatory_role,
        "footer_keywords": list(branding.footer_keywords),
        "footer_text": branding.footer_text,
        "show_wedivo_mention": branding.show_wedivo_mention,
        "monogram": monogram,
        "monogram_color": branding.monogram_color,
        "logo": branding.logo.name or None,
        "logo_on_dark": branding.logo_on_dark.name or None,
        "signature": branding.signature_image.name or None,
        "stamp": branding.stamp_image.name or None,
    }


def build_snapshot(
    *,
    organization_id: str,
    branding: OrganizationBranding,
    monogram: str,
    quote: Any,
    lines: Iterable[Any],
    partners: Iterable[Any],
    client: Any,
) -> dict[str, Any]:
    """Everything the template shows, from a quote (saved or a draft of the editor)."""
    lines = list(lines)
    totals = compute_totals(
        [line.amount for line in lines], Decimal(quote.discount_pct), Decimal(quote.deposit_pct)
    )
    validity_days = max(1, (quote.valid_until - quote.issue_date).days)
    payment_terms = _lines(quote.payment_terms) or _lines(branding.payment_terms)
    template = quote.design or branding.quote_design or DEFAULT_TEMPLATE
    return {
        "version": SNAPSHOT_VERSION,
        "organization_id": str(organization_id),
        "template": template if template in TEMPLATES else DEFAULT_TEMPLATE,
        "palette": palettes.get(quote.palette or branding.quote_palette).code,
        "status": quote.status,
        "agency": agency_snapshot(branding, monogram),
        "partners": [
            {
                "name": partner.name,
                "activity": partner.activity,
                "signatory": partner.signatory,
                "signatory_role": partner.signatory_role,
                "logo": partner.logo.name or None,
                "signature": partner.signature_image.name or None,
            }
            for partner in list(partners)[:2]
        ],
        "quote": {
            "number": quote.number,
            "issue_date": quote.issue_date.isoformat(),
            "valid_until": quote.valid_until.isoformat(),
            "validity_days": validity_days,
            "tagline": quote.tagline or branding.quote_tagline,
            "client": {
                "name": getattr(client, "name", "") or "",
                "phone": getattr(client, "phone", "") or "",
                "email": getattr(client, "email", "") or "",
            },
            "event": {
                "type": quote.event_type or "Mariage",
                "date": quote.wedding_date.isoformat() if quote.wedding_date else None,
                "venue": quote.venue,
                "guests": quote.guest_count,
            },
            "lines": [
                {
                    "label": line.label,
                    "description": line.description,
                    "icon": line.icon
                    or getattr(line.service_item, "icon", "")
                    or icons.guess(line.label),
                    "quantity": _quantity(line.quantity),
                    "unit": line.unit,
                    "unit_price": int(line.unit_price),
                    "amount": int(line.amount),
                }
                for line in lines
            ],
            "subtotal": totals.subtotal,
            "discount_pct": _quantity(quote.discount_pct),
            "discount_amount": totals.discount_amount,
            "total": totals.total,
            "deposit_pct": _quantity(quote.deposit_pct),
            "deposit_amount": totals.deposit_amount,
            "balance": totals.balance,
            "payment_terms": payment_terms
            or default_payment_terms(Decimal(quote.deposit_pct), validity_days),
            "terms": _lines(branding.quote_terms) or default_quote_terms(validity_days),
        },
        # Photos of the palette series (R4b) or uploaded by the agency; None = gradient.
        "photos": {"hero": None, "side": None},
    }


# --- Template context ----------------------------------------------------------------------------


def money(amount: int, *, unit: bool = True) -> str:
    """`1500000` → `1 500 000 FCFA` (narrow no-break spaces, CLAUDE.md §6)."""
    text = f"{amount:,}".replace(",", NNBSP)
    return f"{text}{NBSP}FCFA" if unit else text


def long_date(value: str | None) -> str:
    if not value:
        return ""
    day = date.fromisoformat(value)
    return f"{day.day} {MONTHS[day.month - 1]} {day.year}"


def number(value: str) -> str:
    return value.replace(".", ",")


def fit(text: str, *, base: float, minimum: float, room: int, lines: int = 1) -> dict[str, Any]:
    """Long texts (§3): shrink the font down to `minimum`, then wrap on up to `lines` lines,
    then cut with « … »; never overflow.

    `room` is the number of characters that fit on one line at the `base` size.
    """
    text = (text or "").strip()
    if len(text) <= room:
        return {"text": text, "size": base}
    size = max(minimum, round(base * room / len(text), 2))
    capacity = int(room * base / size) * lines
    if len(text) > capacity:
        text = text[: max(1, capacity - 1)].rstrip() + "…"
    return {"text": text, "size": size}


def _photo(value: str | None) -> str | None:
    if value and value.startswith("data:"):
        return value  # fidelity test only
    return file_url(value)


def context(snapshot: dict[str, Any]) -> dict[str, Any]:
    palette = palettes.get(snapshot["palette"])
    agency = snapshot["agency"]
    quote = snapshot["quote"]
    partners = snapshot["partners"]
    lines = [
        {
            **line,
            "index": index,
            "icon_svg": icons.svg(line["icon"], stroke=1.5),
            "quantity_label": number(line["quantity"]),
            "unit_label": UNIT_LABELS.get(line["unit"], ""),
            "unit_price_label": money(line["unit_price"], unit=False),
            "amount_label": money(line["amount"], unit=False),
            "unit_price_fcfa": money(line["unit_price"]),
            "amount_fcfa": money(line["amount"]),
            "label_fit": fit(line["label"], base=7.6, minimum=6.2, room=38),
            "description_fit": fit(line["description"], base=6, minimum=5, room=58),
        }
        for index, line in enumerate(quote["lines"], start=1)
    ]
    socials = agency["socials"]
    handle = next(iter(socials.values()), "") if socials else ""
    watermark = {"draft": "BROUILLON", "accepted": "ACCEPTÉ"}.get(snapshot["status"], "")
    deposit_pct = Decimal(quote["deposit_pct"])
    schedule = []
    if quote["deposit_amount"]:
        schedule.append(
            {
                "pct": number(quote["deposit_pct"]),
                "ratio": float(deposit_pct / 100),
                "label": "Acompte à la réservation",
                "amount": money(quote["deposit_amount"]),
                "when": "À la signature du devis",
            }
        )
    if quote["balance"]:
        schedule.append(
            {
                "pct": number(_quantity(Decimal(100) - deposit_pct)),
                "ratio": float((Decimal(100) - deposit_pct) / 100),
                "label": "Solde restant",
                "amount": money(quote["balance"]),
                "when": "Au plus tard 7 jours avant l’événement",
            }
        )
    return {
        "s": snapshot,
        "palette_css": palette.css(),
        "p": palette,
        "agency": agency,
        "partners": [
            {
                **partner,
                "logo_url": file_url(partner["logo"]),
                "signature_url": file_url(partner["signature"]),
            }
            for partner in partners
        ],
        "partner": partners[0] if partners else None,
        "quote": quote,
        "lines": lines,
        "logo_url": file_url(agency["logo"]),
        "logo_on_dark_url": file_url(agency["logo_on_dark"]) or file_url(agency["logo"]),
        "signature_url": file_url(agency["signature"]),
        "stamp_url": file_url(agency["stamp"]),
        "hero_photo": _photo(snapshot["photos"].get("hero")),
        "side_photo": _photo(snapshot["photos"].get("side") or snapshot["photos"].get("hero")),
        "name_fit": fit(agency["trade_name"].upper(), base=21, minimum=13, room=11, lines=2),
        "tagline_fit": fit(quote["tagline"], base=9.5, minimum=7, room=90),
        "activities": [
            {**item, "svg": icons.svg(item["icon"], stroke=1.5)} for item in agency["activities"]
        ],
        "engagements": [
            {**item, "svg": icons.svg(item["icon"], stroke=1.6)} for item in agency["engagements"]
        ],
        "scripts": agency["scripts"],
        "thanks_text": agency["footer_text"] or DEFAULT_THANKS,
        "team_signature": agency["signatory"] or f"L’équipe {agency['trade_name']}",
        "phone": agency["phones"][0] if agency["phones"] else agency["whatsapp"],
        "social_handle": handle,
        "social_icons": [icons.svg(name, stroke=1.7) for name in list(socials)[:3]],
        "subtotal": money(quote["subtotal"]),
        "discount": money(quote["discount_amount"]) if quote["discount_amount"] else None,
        "discount_pct": number(quote["discount_pct"]),
        "total": money(quote["total"]),
        "schedule": schedule,
        "issue_date": long_date(quote["issue_date"]),
        "event_date": long_date(quote["event"]["date"]),
        "guests": f"{quote['event']['guests']} personnes" if quote["event"]["guests"] else "",
        "watermark": watermark,
        "icon": {name: icons.svg(name, stroke=1.8) for name in icons.PATHS},
        "fonts": {
            key: asset_url(f"fonts/{file}")
            for key, file in {
                "m400": "montserrat-latin-400-normal.woff",
                "m400i": "montserrat-latin-400-italic.woff",
                "m500": "montserrat-latin-500-normal.woff",
                "m500i": "montserrat-latin-500-italic.woff",
                "m600": "montserrat-latin-600-normal.woff",
                "m700": "montserrat-latin-700-normal.woff",
                "m800": "montserrat-latin-800-normal.woff",
                "p700": "playfair-display-latin-700-normal.woff",
                "p900": "playfair-display-latin-900-normal.woff",
                "gv": "great-vibes-latin-400-normal.woff",
                "al": "allura-latin-400-normal.woff",
            }.items()
        },
    }


def template_path(snapshot: dict[str, Any]) -> str:
    return f"documents/quote_{snapshot['template']}.html"
