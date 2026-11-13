"""The quote of the reference images (docs/rendus/donnees-exemple.json) as a snapshot.

Used by the fidelity test and by `manage.py render_sample` to work on the templates without a
database. Amounts are the computed ones (§2e: the totals printed on the images are wrong).
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.conf import settings

from quotes.calculations import compute_totals

from .quote_document import SNAPSHOT_VERSION, default_payment_terms

SAMPLE_FILE = Path(settings.BASE_DIR).parent / "docs" / "rendus" / "donnees-exemple.json"
ACTIVITY_ICONS = ["rings", "cake", "glass", "briefcase"]
ENGAGEMENT_ICONS = ["star", "team", "clock", "heart"]
ENGAGEMENT_ICONS_B = ["team", "flower", "clock", "heart"]


def load() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SAMPLE_FILE.read_text())
    return data


def quote_snapshot(template: str = "A", palette: str | None = None) -> dict[str, Any]:
    data = load()
    agency, quote = data["agency"], data["quote"]
    lines = [
        {
            "label": line["label"],
            "description": line["description"],
            "icon": line["icon"],
            "quantity": str(line["quantity"]),
            "unit": "unit",
            "unit_price": line["unit_price"],
            "amount": line["quantity"] * line["unit_price"],
        }
        for line in quote["lines"]
    ]
    totals = compute_totals(
        [line["amount"] for line in lines], Decimal(quote["discount_pct"]), Decimal(50)
    )
    engagements = agency["engagements_b"] if template == "B" else agency["engagements"]
    engagement_icons = ENGAGEMENT_ICONS_B if template == "B" else ENGAGEMENT_ICONS
    partner = data["partner"]
    scripts = {key: value for key, value in agency["scripts"].items() if key != "thanks_text"}
    return {
        "version": SNAPSHOT_VERSION,
        "organization_id": "sample",
        "template": template,
        "palette": palette or ("prune-or" if template == "D" else "nuit-or"),
        "status": "sent",
        "agency": {
            "trade_name": agency["trade_name"].replace("'", "’"),
            "legal_name": "",
            "activity": agency["activity"].replace("'", "’"),
            "slogan": agency["slogan"],
            "address": agency["address_d"] if template == "D" else agency["address"],
            "phones": agency["phones"],
            "whatsapp": "",
            "email": agency["email"],
            "website": agency["website"],
            "socials": {k: v for k, v in agency["socials"].items() if k != "whatsapp"},
            "tax_ids": {},
            "vat_rate": None,
            "bank_details": "",
            "mobile_money_numbers": [],
            "activities": [
                {"label": label, "icon": icon}
                for label, icon in zip(agency["activities"], ACTIVITY_ICONS, strict=True)
            ],
            "engagements": [
                {"label": label, "icon": icon}
                for label, icon in zip(engagements, engagement_icons, strict=True)
            ],
            "quote_tagline": agency["quote_tagline"],
            "scripts": scripts,
            "signatory": agency["signatory"].replace("'", "’"),
            "signatory_role": agency["signatory_role"],
            "footer_keywords": agency["footer_keywords"],
            "footer_text": "",
            "show_wedivo_mention": False,
            "monogram": "M",
            "monogram_color": "",
            "logo": None,
            "logo_on_dark": None,
            "signature": None,
            "stamp": None,
        },
        "partners": (
            [
                {
                    "name": partner["name"],
                    "activity": partner["activity"],
                    "signatory": "",
                    "signatory_role": partner["signatory_role"],
                    "logo": None,
                    "signature": None,
                }
            ]
            if template == "D"
            else []
        ),
        "quote": {
            "number": quote["number"],
            "issue_date": quote["issue_date"],
            "valid_until": "2027-03-16",
            "validity_days": 30,
            "tagline": (
                "Une organisation sur mesure pour un jour inoubliable."
                if template == "D"
                else agency["quote_tagline"]
            ),
            "client": {
                "name": quote["client"]["name"],
                "phone": quote["client"]["phone"],
                "email": quote["client"]["email"],
            },
            "event": {
                "type": quote["event"]["type"],
                "date": quote["event"]["date"],
                "venue": quote["event"]["venue"],
                "guests": quote["event"]["guests"],
            },
            "lines": lines,
            "subtotal": totals.subtotal,
            "discount_pct": str(quote["discount_pct"]),
            "discount_amount": totals.discount_amount,
            "total": totals.total,
            "deposit_pct": "50",
            "deposit_amount": totals.deposit_amount,
            "balance": totals.balance,
            "payment_terms": [t.replace("50%", "50 %") for t in quote["payment_terms"]]
            or default_payment_terms(Decimal(50), 30),
            "terms": quote["terms_d"],
        },
        "photos": {"hero": None, "side": None},
    }


TICKET_PALETTES = {"or-noir": "noir-or", "bleu-royal": "bleu-royal", "emeraude": "emeraude-or"}


def ticket_snapshot(variant: str = "or-noir") -> dict[str, Any]:
    """The ticket of the reference images (billets/billet-{variant}.jpg)."""
    from types import SimpleNamespace

    from .ticket_document import build_snapshot

    data = load()["tickets"]
    common, own = data["common"], data[variant]
    design = SimpleNamespace(
        palette=TICKET_PALETTES[variant],
        partner_1=own["partner_1"],
        partner_2=own["partner_2"],
        title=common["title"],
        subtitle=common["subtitle"],
        intro=common["intro"].replace("'", "’"),
        panel_text=own.get("panel_text") or "",
        bottom_slogan=own.get("bottom_slogan") or "",
        script_line=own["script_line"],
        venue=common["venue"],
        address=common["city"],
        dress_code=common["dress_code"],
        stub_title=common["stub_title"].replace("'", "’"),
        stub_subtitle=common["stub_subtitle"],
        stub_script=common["stub_script"],
        stub_footer=own["stub_footer"],
        show_monogram=bool(own.get("monogram")),
        starts_at=None,
    )
    snapshot = build_snapshot(
        organization_id="00000000-0000-0000-0000-000000000000",
        slug="sample",
        timezone="Africa/Douala",
        design=design,
        agency={"logo": None, "trade_name": "M’PLANNER"},
        guest={**common["guest_example"], "category": "", "table": ""},
        ticket={"code": common["code"], "token_id": "00" * 16},
    )
    snapshot["design"]["starts_at"] = "2025-05-24T15:00:00+01:00"
    return snapshot
