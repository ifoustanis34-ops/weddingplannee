"""Line icons of the documents (docs/specs/devis-billets.md §2e), drawn on a 24 × 24 grid.

They take ``currentColor``: each template colours them with the palette. Shapes follow the
lucide set (ISC licence) so that documents and interface speak the same visual language.
"""

from __future__ import annotations

from django.utils.safestring import SafeString, mark_safe

PATHS: dict[str, str] = {
    # --- Services of the catalogue ---
    "table": '<path d="M3 8h18"/><path d="M5 8v11"/><path d="M19 8v11"/><path d="M5 13h14"/>'
    '<path d="M8 5h8"/>',
    "chair": '<path d="M7 3h10v8H7z"/><path d="M5 11h14v3H5z"/><path d="M7 14v7"/>'
    '<path d="M17 14v7"/>',
    "flower": '<circle cx="12" cy="12" r="2.5"/><path d="M12 9.5a3 3 0 1 1 0-6 3 3 0 1 1 0 6"/>'
    '<path d="M12 14.5a3 3 0 1 0 0 6 3 3 0 1 0 0-6"/>'
    '<path d="M9.5 12a3 3 0 1 1-6 0 3 3 0 1 1 6 0"/>'
    '<path d="M14.5 12a3 3 0 1 0 6 0 3 3 0 1 0-6 0"/>',
    "bouquet": '<circle cx="9" cy="7" r="2.5"/><circle cx="15" cy="7" r="2.5"/>'
    '<circle cx="12" cy="4.5" r="2.5"/><path d="M8 10l4 5 4-5"/><path d="M12 15v6"/>'
    '<path d="M9 21h6"/>',
    "arch": '<path d="M5 21V10a7 7 0 0 1 14 0v11"/><path d="M8.5 21v-10a3.5 3.5 0 0 1 7 0v10"/>'
    '<path d="M3 21h18"/>',
    "camera": '<path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 '
    '0 0-2-2h-3z"/><circle cx="12" cy="13" r="3.5"/>',
    "video": '<path d="M16 13l5.2 3.5a.5.5 0 0 0 .8-.4V7.9a.5.5 0 0 0-.8-.4L16 11"/>'
    '<rect x="2" y="6" width="14" height="12" rx="2"/>',
    "speaker": '<rect x="5" y="2" width="14" height="20" rx="2"/><circle cx="12" cy="14" r="4"/>'
    '<path d="M12 6h.01"/>',
    "mic": '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/>'
    '<path d="M19 10v2a7 7 0 0 1-14 0v-2"/><path d="M12 19v3"/>',
    "light": '<path d="M9 18h6"/><path d="M10 22h4"/><path d="M15 14c.2-1 .7-1.7 1.5-2.5A4.6 '
    '4.6 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.8.8 1.3 1.5 1.5 2.5"/>',
    "tools": '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.8-3.8a6 6 0 0 1-7.9 '
    '7.9l-6.9 6.9a2.1 2.1 0 0 1-3-3l6.9-6.9a6 6 0 0 1 7.9-7.9z"/>',
    "plate": '<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="3.5"/>'
    '<path d="M2 4v6a2 2 0 0 0 2 2"/><path d="M22 4v16"/>',
    "cake": '<path d="M20 21v-8a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8"/><path d="M4 16s.5-1 2-1 2.5 2 '
    '4 2 2.5-2 4-2 2.5 2 4 2 2-1 2-1"/><path d="M2 21h20"/><path d="M7 8v3"/><path d="M12 8v3"/>'
    '<path d="M17 8v3"/><path d="M7 4h.01"/><path d="M12 4h.01"/><path d="M17 4h.01"/>',
    "glass": '<path d="M8 22h8"/><path d="M12 15v7"/><path d="M5 3h14l-7 12z"/>'
    '<path d="M7.5 7h9"/>',
    "car": '<path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9L18 10l-2.7-3.6A2 2 0 0 0 13.7 '
    '6H7.3a2 2 0 0 0-1.6.8L3 10.5V16c0 .6.4 1 1 1h2"/><circle cx="7.5" cy="17" r="2"/>'
    '<circle cx="16.5" cy="17" r="2"/><path d="M9.5 17h5"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4"/>'
    '<path d="M8 2v4"/><path d="M3 10h18"/>',
    "calendar-check": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4"/>'
    '<path d="M8 2v4"/><path d="M3 10h18"/><path d="M9 16l2 2 4-4"/>',
    "clipboard": '<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 '
    '2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M9 12h6"/>'
    '<path d="M9 16h6"/>',
    "music": '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/>'
    '<circle cx="18" cy="16" r="3"/>',
    "gift": '<rect x="3" y="8" width="18" height="4" rx="1"/><path d="M12 8v13"/>'
    '<path d="M19 12v7a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-7"/><path d="M7.5 8a2.5 2.5 0 0 1 0-5C10 3 '
    '12 8 12 8s2-5 4.5-5a2.5 2.5 0 0 1 0 5"/>',
    # --- Activities and engagements of the agency ---
    "rings": '<circle cx="9" cy="14" r="6"/><circle cx="15" cy="14" r="6"/><path d="M10 4l2-2 '
    '2 2-2 2z"/>',
    "briefcase": '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 '
    '0-2-2h-4a2 2 0 0 0-2 2v16"/>',
    "star": '<path d="M12 2l3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1z"/>',
    "team": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
    '<path d="M22 21v-2a4 4 0 0 0-3-3.9"/><path d="M16 3.1a4 4 0 0 1 0 7.8"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "heart": '<path d="M19 14c1.5-1.5 3-3.2 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.8 0-3 .5-4.5 2-1.5-1.5'
    '-2.7-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4 3 5.5l7 7z"/>',
    "shield": '<path d="M20 13c0 5-3.5 7.5-7.7 9a1 1 0 0 1-.7 0C7.5 20.5 4 18 4 13V6a1 1 0 0 1 '
    '1-1c2 0 4.5-1.2 6.2-2.7a1.2 1.2 0 0 1 1.5 0C14.5 3.8 17 5 19 5a1 1 0 0 1 1 1z"/>'
    '<path d="M9 12l2 2 4-4"/>',
    "sparkles": '<path d="M9.9 15.5A2 2 0 0 0 8.5 14l-6.1-1.6a.5.5 0 0 1 0-1L8.5 9.9A2 2 0 0 0 '
    "9.9 8.5l1.6-6.1a.5.5 0 0 1 1 0l1.6 6.1a2 2 0 0 0 1.4 1.4l6.1 1.6a.5.5 0 0 1 0 1l-6.1 1.6a2 "
    '2 0 0 0-1.4 1.4l-1.6 6.1a.5.5 0 0 1-1 0z"/>',
    "dress": '<path d="M9 2h6l-1 4 3 4-1 2 3 10H5l3-10-1-2 3-4z"/><path d="M10 6h4"/>',
    "smartphone": '<rect x="6" y="2" width="12" height="20" rx="2"/><path d="M11 18h2"/>',
    # --- Information and totals ---
    "user": '<circle cx="12" cy="8" r="5"/><path d="M20 21a8 8 0 0 0-16 0"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
    '<path d="M22 21v-2a4 4 0 0 0-3-3.9"/><path d="M16 3.1a4 4 0 0 1 0 7.8"/>',
    "phone": '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 '
    "19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 "
    '9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z"/>',
    "mail": '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 7l-10 6L2 7"/>',
    "pin": '<path d="M20 10c0 5-5.5 10.2-7.4 11.8a1 1 0 0 1-1.2 0C9.5 20.2 4 15 4 10a8 8 0 0 1 '
    '16 0"/><circle cx="12" cy="10" r="3"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 '
    '0 0-20"/><path d="M2 12h20"/>',
    "calculator": '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 6h8"/>'
    '<path d="M16 14v4"/><path d="M16 10h.01"/><path d="M12 10h.01"/><path d="M8 10h.01"/>'
    '<path d="M12 14h.01"/><path d="M8 14h.01"/><path d="M12 18h.01"/><path d="M8 18h.01"/>',
    "coins": '<circle cx="8" cy="8" r="6"/><path d="M18.1 10.4A6 6 0 1 1 10.3 18"/>'
    '<path d="M7 6h1v4"/><path d="M16.7 13.9l.7.7-2.8 2.8"/>',
    "wallet": '<path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 '
    '4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1"/><path d="M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"/>',
    "card": '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20"/>',
    "document": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z"/>'
    '<path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/>'
    '<path d="M16 17H8"/>',
    "tag": '<path d="M12.6 2.6A2 2 0 0 0 11.2 2H4a2 2 0 0 0-2 2v7.2a2 2 0 0 0 .6 1.4l8.7 8.7a2.4 '
    '2.4 0 0 0 3.4 0l6.6-6.6a2.4 2.4 0 0 0 0-3.4z"/><circle cx="7.5" cy="7.5" r="1"/>',
    # --- Social networks (simplified marks) ---
    "facebook": '<path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/>',
    "instagram": '<rect x="2" y="2" width="20" height="20" rx="5"/><circle cx="12" cy="12" r="4"/>'
    '<path d="M17.5 6.5h.01"/>',
    "tiktok": '<path d="M9 12a4 4 0 1 0 4 4V2a5 5 0 0 0 5 5"/>',
    "whatsapp": '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22z"/><path d="M9 10a.5.5 0 0 0 1 0V9a.5.5 '
    '0 0 0-1 0v1a5 5 0 0 0 5 5h1a.5.5 0 0 0 0-1h-1a.5.5 0 0 0 0 1"/>',
    "linkedin": '<path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-4 0v7h-4v-7a6 6 0 0 1 6-6z"/>'
    '<rect x="2" y="9" width="4" height="12"/><circle cx="4" cy="4" r="2"/>',
    "youtube": '<path d="M2.5 17a24 24 0 0 1 0-10 2 2 0 0 1 1.4-1.4 49.6 49.6 0 0 1 16.2 0A2 2 0 '
    '0 1 21.5 7a24 24 0 0 1 0 10 2 2 0 0 1-1.4 1.4 49.6 49.6 0 0 1-16.2 0A2 2 0 0 1 2.5 17"/>'
    '<path d="M10 15l5-3-5-3z"/>',
}
# Catalogue services and agency items fall back to a neutral mark.
FALLBACK = "sparkles"
SERVICE_ICONS = sorted(
    [
        "table",
        "chair",
        "flower",
        "bouquet",
        "arch",
        "camera",
        "video",
        "speaker",
        "mic",
        "light",
        "tools",
        "plate",
        "cake",
        "glass",
        "car",
        "calendar",
        "calendar-check",
        "clipboard",
        "music",
        "gift",
        "sparkles",
    ]
)


def svg(name: str, *, stroke: float = 1.8, cls: str = "ic") -> SafeString:
    """Inline SVG; ``currentColor`` so that the template sets the colour."""
    body = PATHS.get(name) or PATHS[FALLBACK]
    return mark_safe(  # noqa: S308 - static markup from this module only
        f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )


# Keyword → icon, checked in order on the service name (accents removed, lower case).
GUESSES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("chaise",), "chair"),
    (("table",), "table"),
    (("arche",), "arch"),
    (("bouquet", "fleur", "floral"), "bouquet"),
    (("decor", "centre de table"), "flower"),
    (("photo",), "camera"),
    (("video", "film", "drone"), "video"),
    (("dj", "sono", "son "), "speaker"),
    (("orchestre", "musique", "chorale", "animation"), "music"),
    (("micro", "maitre de ceremonie", "mc "), "mic"),
    (("lumiere", "eclairage"), "light"),
    (("installation", "montage", "logistique"), "tools"),
    (("gateau", "piece montee"), "cake"),
    (("traiteur", "menu", "repas", "restauration", "buffet"), "plate"),
    (("boisson", "cocktail", "champagne", "bar"), "glass"),
    (("transport", "voiture", "vehicule"), "car"),
    (("coordination", "jour j", "accompagnement", "planning"), "calendar-check"),
    (("invitation", "faire-part", "papeterie"), "clipboard"),
    (("cadeau",), "gift"),
)


def guess(label: str) -> str:
    """An icon for a service from its name (« Location de chaises » → chair)."""
    import unicodedata

    text = "".join(
        c for c in unicodedata.normalize("NFD", f"{label.lower()} ") if not unicodedata.combining(c)
    )
    for keywords, icon in GUESSES:
        if any(keyword in text for keyword in keywords):
            return icon
    return FALLBACK
