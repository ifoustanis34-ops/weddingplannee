"""Ticket documents « Ticket détachable » (docs/specs/devis-billets.md §2b, §6, §7).

Like the quotes, a ticket is rendered from a frozen snapshot. The snapshot keeps the ticket's
token id, not the token: the QR is signed again at rendering with the organization's key.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from django.conf import settings

from . import barcodes, icons, palettes, qr
from .quote_document import fit
from .rendering import asset_url, file_url

SNAPSHOT_VERSION = 1
TEMPLATE = "documents/ticket.html"
DEFAULT_PALETTE = "noir-or"
DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
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
PREVIEW_GUEST = {"name": "Famille Kouassi", "seats": 4, "category": "Famille", "table": ""}


def ticket_url(slug: str, token: str) -> str:
    """The QR's content: the guest's page, also recognised by the scan app (§7)."""
    if settings.TICKET_LINKS_ON_SUBDOMAIN:
        return f"https://{slug}.{settings.TENANT_BASE_DOMAIN}/t/{token}"
    return f"{settings.FRONTEND_URL}/t/{token}"


def initials(design: Any, wedding_title: str) -> str:
    """Two letters of the couple for the readable code (« WDV-DG-0001 »)."""
    import unicodedata

    names = [design.partner_1, design.partner_2] if design.partner_1 else wedding_title.split("&")
    letters = ""
    for name in names:
        name = unicodedata.normalize("NFD", name.strip())
        first = next((c for c in name if c.isalpha() and c.isascii()), "")
        letters += first.upper()
    return (letters + "XX")[:2]


def design_snapshot(design: Any) -> dict[str, Any]:
    fields = (
        "palette",
        "partner_1",
        "partner_2",
        "title",
        "subtitle",
        "intro",
        "panel_text",
        "bottom_slogan",
        "script_line",
        "venue",
        "address",
        "dress_code",
        "stub_title",
        "stub_subtitle",
        "stub_script",
        "stub_footer",
        "show_monogram",
    )
    data = {field: getattr(design, field) for field in fields}
    data["starts_at"] = design.starts_at.isoformat() if design.starts_at else None
    return data


def build_snapshot(
    *,
    organization_id: str,
    slug: str,
    timezone: str,
    design: Any,
    agency: dict[str, Any],
    guest: dict[str, Any],
    ticket: dict[str, Any] | None,
    status: str = "active",
) -> dict[str, Any]:
    """`ticket` = {code, token_id} for a real ticket, None for the design preview."""
    return {
        "version": SNAPSHOT_VERSION,
        "kind": "ticket",
        "organization_id": str(organization_id),
        "slug": slug,
        "timezone": timezone,
        "status": status,
        "design": design_snapshot(design),
        "agency": agency,
        "guest": guest,
        "ticket": ticket,
        "photos": {"main": None},
    }


def _when(value: str | None, timezone: str) -> dict[str, str]:
    if not value:
        return {"day": "", "date": "Date à confirmer", "time": "", "full": "Date à confirmer"}
    moment = datetime.fromisoformat(value).astimezone(ZoneInfo(timezone))
    day = DAYS[moment.weekday()].capitalize()
    date = f"{moment.day} {MONTHS[moment.month - 1]} {moment.year}"
    time = f"{moment.hour:02d}h{moment.minute:02d}"
    return {"day": day, "date": date, "time": f"à {time}", "full": f"{day} {date} à {time}"}


def _token(snapshot: dict[str, Any]) -> str | None:
    from uuid import UUID

    from invitations import tokens

    ticket = snapshot["ticket"]
    if not ticket or not ticket.get("token_id"):
        return None
    return tokens.token_for(UUID(snapshot["organization_id"]), ticket["token_id"])


def context(snapshot: dict[str, Any]) -> dict[str, Any]:
    design = snapshot["design"]
    palette = palettes.get(design["palette"] or DEFAULT_PALETTE)
    ticket = snapshot["ticket"]
    token = _token(snapshot)
    url = (
        ticket_url(snapshot["slug"], token)
        if token
        else f"{settings.FRONTEND_URL}/t/apercu-du-billet"
    )
    code = ticket["code"] if ticket else "WDV-XX-0001"
    guest = snapshot["guest"]
    seats = guest["seats"]
    guest_line = f"{guest['name']} · {seats} place{'s' if seats > 1 else ''}"
    when = _when(design["starts_at"], snapshot["timezone"])
    monogram = (design["partner_1"][:1] + design["partner_2"][:1]).upper()
    return {
        "s": snapshot,
        "p": palette,
        "palette_css": palette.css(),
        "d": design,
        "agency": snapshot["agency"],
        "logo_url": file_url(snapshot["agency"].get("logo")),
        "when": when,
        "name_1": fit(design["partner_1"] or "Prénom", base=40, minimum=24, room=8),
        "name_2": fit(design["partner_2"] or "Prénom", base=48, minimum=28, room=8),
        "intro": fit(design["intro"], base=8.6, minimum=7, room=140),
        "guest_line": fit(guest_line, base=7.4, minimum=5.8, room=34),
        "category": guest.get("category", ""),
        "table": guest.get("table", ""),
        "code": code,
        "qr_svg": qr.svg(url),
        "barcode_svg": barcodes.svg(code, vertical=True),
        "monogram": monogram if design["show_monogram"] else "",
        "photo": snapshot["photos"].get("main"),
        "watermark": "ANNULÉ" if snapshot["status"] in ("cancelled", "reissued") else "",
        "icon": {name: icons.svg(name, stroke=1.6) for name in icons.PATHS},
        "fonts": {
            key: asset_url(f"fonts/{file}")
            for key, file in {
                "m400": "montserrat-latin-400-normal.woff",
                "m500": "montserrat-latin-500-normal.woff",
                "m600": "montserrat-latin-600-normal.woff",
                "m700": "montserrat-latin-700-normal.woff",
                "p900": "playfair-display-latin-900-normal.woff",
                "gv": "great-vibes-latin-400-normal.woff",
            }.items()
        },
    }
