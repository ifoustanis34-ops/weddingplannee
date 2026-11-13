"""Identities of the demo agencies (seed_demo): two different looks to check the documents."""

from __future__ import annotations

from typing import Any

from . import services


def monogram_logo(initials: str, name: str, primary: str, accent: str) -> bytes:
    """A simple vector logo (initials in a ring, the name below); no third-party artwork."""
    return (
        f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 200" width="320" height="200">
  <circle cx="160" cy="72" r="54" fill="none" stroke="{accent}" stroke-width="4"/>
  <circle cx="160" cy="72" r="46" fill="none" stroke="{accent}" stroke-width="1.2"/>
  <text x="160" y="90" text-anchor="middle" font-family="Playfair Display, Georgia, serif"
    font-size="48" font-weight="700" fill="{primary}">{initials}</text>
  <text x="160" y="170" text-anchor="middle" font-family="Montserrat, Arial, sans-serif"
    font-size="19" font-weight="600" letter-spacing="4" fill="{primary}">{name}</text>
</svg>""".encode()
    )


MAISON_ELEGANCE: dict[str, Any] = {
    "primary_color": "#0F1B3D",
    "secondary_color": "#C9A24A",
    "monogram_color": "#C9A24A",
    "use_brand_colors": True,
    "trade_name": "Maison Élégance Events",
    "legal_name": "Maison Élégance Events SARL",
    "activity": "Gestion & organisation d’événements",
    "slogan": "Vos rêves, notre organisation",
    "address": "Rue Njo-Njo, Bonapriso, Douala, Cameroun",
    "phones": ["+237 620 81 23 45", "+237 604 42 10 98"],
    "whatsapp": "+237 620 81 23 45",
    "email": "contact@maison-elegance.cm",
    "website": "maison-elegance.cm",
    "socials": {"facebook": "Maison Élégance Events", "instagram": "@maisonelegance.cm"},
    "tax_ids": {"rccm": "RC/DLA/2019/B/1234", "niu": "M061912345678A"},
    "bank_details": "NSIA Banque · CI042 01001 012345678901 23",
    "mobile_money_numbers": [{"provider": "Orange Money", "number": "+237 620 81 23 45"}],
    "signatory": "Aïcha Koné",
    "signatory_role": "Directrice",
    "quote_tagline": "Une organisation sur mesure pour le plus beau jour de votre vie.",
    "payment_terms": "Acompte de 40 % à la signature, solde 7 jours avant l’événement.",
    "footer_text": "Merci de votre confiance.",
}
MAISON_LOGO = monogram_logo("ME", "MAISON ÉLÉGANCE", "#0F1B3D", "#C9A24A")

ATELIER_BASSAM: dict[str, Any] = {
    "primary_color": "#0B4D3B",
    "secondary_color": "#D9A441",
    "monogram_color": "#D9A441",
    "use_brand_colors": True,
    "trade_name": "Atelier Kribi Mariages",
    "legal_name": "Atelier Kribi SARL",
    "activity": "Wedding planner & décoration",
    "slogan": "L’élégance au bord de la lagune",
    "address": "Quartier Mokolo, Kribi, Cameroun",
    "phones": ["+237 625 93 32 21"],
    "whatsapp": "+237 625 93 32 21",
    "email": "bonjour@atelier-kribi.cm",
    "website": "",
    "socials": {"instagram": "@atelierbassam"},
    "tax_ids": {"rccm": "CI-GBS-2022-B-00987"},
    "activities": [
        {"label": "Mariages", "icon": "rings"},
        {"label": "Dots et fiançailles", "icon": "heart"},
        {"label": "Décoration florale", "icon": "flower"},
        {"label": "Réceptions", "icon": "glass"},
    ],
    "signatory": "Koffi N’Guessan",
    "signatory_role": "Gérant",
    "show_wedivo_mention": False,
}
ATELIER_LOGO = monogram_logo("AB", "ATELIER BASSAM", "#0B4D3B", "#D9A441")


def apply(data: dict[str, Any], logo: bytes) -> None:
    """Set the active organization's identity; the logo is uploaded once (kept afterwards)."""
    branding = services.get_branding()
    services.update_branding(branding, data)
    if not branding.logo:
        services.store_file(branding, "logo", logo)
