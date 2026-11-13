"""Staff badges (feedback 13/11/2026): credit-card size, in four designs, with the agency's logo
and palette, the photo (or initials), name, position and a QR code `WDV1:STAFF:<id>`.

- `classique`: landscape, colored band, large photo.
- `portrait`: vertical, round photo on top — the badge worn on a lanyard.
- `elegant`: dark background, gold accents, serif name.
- `minimal`: white, colored side stripe, sober.

Sheets are A4 with absolutely positioned cards and dashed cut lines; `preview` renders a single
card (PNG) to choose the design on screen.
"""

from __future__ import annotations

import base64
import functools
from collections.abc import Iterable
from dataclasses import dataclass

from django.template.loader import render_to_string
from PIL import ImageFont

from core.exceptions import BusinessError
from core.tenant import require_current_organization
from documents import palettes, qr, rendering
from documents import services as branding_services

from .models import StaffMember


@dataclass(frozen=True)
class Layout:
    width: float  # mm
    height: float
    cols: int
    rows: int
    gap: float = 6.0


DESIGNS = {
    "carte": Layout(54.0, 85.6, 3, 3, gap=5.0),  # front + back, reference of 13/11/2026
    "classique": Layout(85.6, 54.0, 2, 4),
    "portrait": Layout(54.0, 85.6, 3, 3, gap=5.0),
    "elegant": Layout(85.6, 54.0, 2, 4),
    "minimal": Layout(85.6, 54.0, 2, 4),
}
LABELS = {
    "carte": "Carte employé",
    "classique": "Classique",
    "portrait": "Portrait",
    "elegant": "Élégant",
    "minimal": "Minimal",
}


def payload(staff: StaffMember) -> str:
    return f"WDV1:STAFF:{staff.pk}"


def _photo(staff: StaffMember) -> str | None:
    """The private photo embedded in the PDF (works with any storage, never a public URL)."""
    if not staff.photo:
        return None
    try:
        with staff.photo.open("rb") as handle:
            content = handle.read()
    except OSError:
        return None
    extension = staff.photo.name.rsplit(".", 1)[-1].lower()
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(extension, "jpeg")
    return f"data:image/{mime};base64,{base64.b64encode(content).decode()}"


def initials(name: str) -> str:
    words = [w for w in name.split() if w[:1].isalpha()]
    return "".join(w[0].upper() for w in words[:2]) or "?"


def _html(people: Iterable[StaffMember], design: str, *, preview: bool) -> str:
    if design not in DESIGNS:
        raise BusinessError("invalid", "Modèle de badge inconnu.", {"design": [design]})
    if design == "carte":
        return _card_html(list(people), preview=preview)
    layout = DESIGNS[design]
    organization = require_current_organization()
    branding = branding_services.get_branding()
    palette = palettes.get(branding.quote_palette)
    qr_dark = palette.dark  # always dark on white: what every phone scans reliably
    badges = [
        {
            "name": person.full_name,
            "position": person.position,
            "kind": person.get_kind_display(),
            "photo": _photo(person),
            "initials": initials(person.full_name),
            "qr": qr.svg(payload(person), dark=qr_dark),
            "phone": person.emergency_contact,
        }
        for person in people
    ]
    per_page = layout.cols * layout.rows
    for index, badge in enumerate(badges):
        slot = index % per_page
        # Text, not floats: the French locale would print « 91,6 » in the CSS.
        badge["left"] = f"{(slot % layout.cols) * (layout.width + layout.gap):.1f}mm"
        badge["top"] = f"{(slot // layout.cols) * (layout.height + layout.gap):.1f}mm"
    pages = [badges[i : i + per_page] for i in range(0, len(badges), per_page)]
    return render_to_string(
        "staff/badges.html",
        {
            "pages": pages,
            "design": design,
            "preview": preview,
            "w": f"{layout.width:.1f}mm",
            "h": f"{layout.height:.1f}mm",
            "agency": branding.trade_name or organization.name,
            "logo": branding_services.logo_data_uri(),
            "p": palette,
            "fonts": {
                "m400": rendering.asset_url("fonts/montserrat-latin-400-normal.woff"),
                "m700": rendering.asset_url("fonts/montserrat-latin-700-normal.woff"),
                "p700": rendering.asset_url("fonts/playfair-display-latin-700-normal.woff"),
            },
        },
    )


# --- Text fitting: every line stays where the reference puts it, whatever its length -------------

_PT_TO_MM = 25.4 / 72


@functools.lru_cache(maxsize=16)
def _font(weight: str) -> ImageFont.FreeTypeFont:
    path = rendering.DOCUMENTS_DIR / "fonts" / f"montserrat-latin-{weight}.woff"
    return ImageFont.truetype(str(path), 100)


def text_width(text: str, weight: str, size_pt: float, spacing_mm: float = 0.0) -> float:
    """Width in mm of `text` in Montserrat (`weight` like « 700-normal »)."""
    length = _font(weight).getlength(text) / 100 * size_pt * _PT_TO_MM
    return length + spacing_mm * max(len(text) - 1, 0)


def fit(text: str, weight: str, size_pt: float, width_mm: float, spacing_mm: float = 0.0) -> str:
    """The reference size, smaller only when the text would not fit `width_mm` (never < 55 %)."""
    width = text_width(text, weight, size_pt, spacing_mm)
    size = size_pt if width <= width_mm else max(size_pt * width_mm / width, size_pt * 0.55)
    return f"{size:.2f}pt"


def two_lines(text: str) -> list[str]:
    """« Ensemble, construisons / un avenir digital. »: the motto on two balanced lines, the first
    one at least as long as the second, like the reference."""
    words = text.split()
    if len(words) < 2:
        return [text]
    best: list[str] = [text]
    best_score: tuple[int, int] | None = None
    for cut in range(1, len(words)):
        first, second = " ".join(words[:cut]), " ".join(words[cut:])
        score = (max(len(first), len(second)), 0 if len(first) >= len(second) else 1)
        if best_score is None or score < best_score:
            best, best_score = [first, second], score
    return best


# --- « Carte employé »: front and back ------------------------------------------------------------

GLYPHS = {
    # The reference's icons: gold briefcase, white badge and phone; white line-art towers.
    "briefcase": '<svg viewBox="0 0 24 24"><rect x="2.5" y="7" width="19" height="13" rx="2" '
    'fill="#e7c169"/><path d="M9 7V5.2A1.7 1.7 0 0 1 10.7 3.5h2.6A1.7 1.7 0 0 1 15 5.2V7" '
    'fill="none" stroke="#e7c169" stroke-width="2"/><path d="M2.5 12.5h19" stroke="#2b1252" '
    'stroke-width="1.6"/><rect x="10.5" y="11" width="3" height="3" rx=".6" fill="#2b1252"/></svg>',
    "id": '<svg viewBox="0 0 24 24"><rect x="5" y="3.5" width="14" height="18" rx="2" fill="#fff"/>'
    '<rect x="9.5" y="2" width="5" height="3" rx="1" fill="#fff" stroke="#2b1252" '
    'stroke-width="1"/>'
    '<circle cx="12" cy="11" r="2.6" fill="#2b1252"/><path d="M7.8 18c.8-2.6 7.6-2.6 8.4 0" '
    'fill="#2b1252"/></svg>',
    "phone": '<svg viewBox="0 0 24 24"><path fill="#fff" d="M6.6 10.8a15.2 15.2 0 0 0 6.6 6.6l2.2'
    "-2.2a1 1 0 0 1 1-.25 11.4 11.4 0 0 0 3.6.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1"
    ' 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.45.57 3.57a1 1 0 0 1-.25 1z"/></svg>',
    "building": '<svg viewBox="0 0 60 40" fill="none" stroke="#fff" stroke-width=".9" '
    'stroke-linejoin="round" stroke-linecap="round"><path d="M1 39h58"/><path d="M7 39V17l8-3v25"/>'
    '<path d="M15 39V9l9-5 9 5v30"/><path d="M24 4v35"/><path d="M33 39V12l10 3v24"/>'
    '<path d="M43 39V22l9 2v15"/><path d="M10 21h3M10 25h3M10 29h3M10 33h3M18 13h3M18 17h3M18 21h'
    "3M18 25h3M18 29h3M18 33h3M27 13h3M27 17h3M27 21h3M27 25h3M27 29h3M27 33h3M36 18h4M36 22h4M36"
    ' 26h4M36 30h4M36 34h4M46 27h3M46 31h3M46 35h3"/></svg>',
}
CARD_LABELS = {
    StaffMember.Kind.EMPLOYEE: "CARTE EMPLOYÉ",
    StaffMember.Kind.DAY_WORKER: "CARTE PERSONNEL",
    StaffMember.Kind.FREELANCE: "CARTE PRESTATAIRE",
}


def _values(branding: object) -> str:
    """« Innovation • Excellence • Confiance »: the agency's engagements (3 first)."""
    engagements = [
        str(item.get("label", "")).strip()
        for item in getattr(branding, "engagements", []) or []
        if isinstance(item, dict)
    ]
    words = [w for w in engagements if w][:3]
    # Short values only (« Innovation • Excellence • Confiance »): sentences do not fit a card.
    if len(words) == 3 and all(len(w) <= 18 for w in words):
        return " • ".join(words)
    return "Rigueur • Élégance • Confiance"


def _values_html(values: str) -> str:
    """« Innovation • Excellence • Confiance » with the reference's gold dots."""
    from django.utils.html import escape

    return '<span class="dot">•</span>'.join(escape(v.strip()) for v in values.split("•"))


def _card_html(people: list[StaffMember], *, preview: bool) -> str:
    from . import services

    layout = DESIGNS["carte"]
    organization = require_current_organization()
    branding = branding_services.get_branding()
    palette = palettes.get(branding.quote_palette)
    cards = [
        {
            "name": person.full_name,
            "position": person.position,
            "department": person.department or person.position,
            "number": services.ensure_employee_number(person),
            "phone": person.phone or "—",
            "photo": _photo(person),
            "initials": initials(person.full_name),
            "card_label": CARD_LABELS.get(StaffMember.Kind(person.kind), "CARTE PERSONNEL"),
            "name_size": fit(person.full_name, "800-normal", 14.2, 50.0, -0.18),
            "role_size": fit(person.position, "500-normal", 8.5, 50.0, -0.1),
            "row_size": fit(
                max(
                    f"Département : {person.department or person.position}",
                    f"Contact : {person.phone or '—'}",
                    key=len,
                ),
                "600-normal",
                6.3,
                39.0,
                -0.1,
            ),
            # The QR opens the public check page « Badge valide » (signed, no private data).
            "qr": qr.svg(services.badge_url(person), dark="#000000"),
        }
        for person in people
    ]
    per_page = layout.cols * layout.rows
    pages: list[dict[str, object]] = []
    if preview:  # one person: front and back side by side
        front = {**cards[0], "left": "0mm", "top": "0mm"}
        back = {**cards[0], "left": "58mm", "top": "0mm"}
        pages = [{"side": "f", "cards": [front]}, {"side": "b", "cards": [back]}]
    else:
        for start in range(0, len(cards), per_page):
            chunk = cards[start : start + per_page]
            fronts, backs = [], []
            for slot, card in enumerate(chunk):
                col, row = slot % layout.cols, slot // layout.cols
                top = f"{row * (layout.height + layout.gap):.1f}mm"
                fronts.append(
                    {**card, "left": f"{col * (layout.width + layout.gap):.1f}mm", "top": top}
                )
                # Mirrored column: the back falls behind its front once printed double-sided.
                mirrored = layout.cols - 1 - col
                backs.append(
                    {**card, "left": f"{mirrored * (layout.width + layout.gap):.1f}mm", "top": top}
                )
            pages += [{"side": "f", "cards": fronts}, {"side": "b", "cards": backs}]
    trade = branding.trade_name or organization.name
    company = branding.legal_name or trade
    motto = branding.slogan or branding.quote_tagline
    motto_lines = two_lines(motto) if motto else []
    return render_to_string(
        "staff/badge_card.html",
        {
            "pages": pages,
            "preview": preview,
            "preview_w": "112mm",
            "agency": trade,
            "logo": branding_services.logo_data_uri(),
            "p": palette,
            "icons": GLYPHS,
            "motto_lines": motto_lines,
            "motto_size": min(
                (fit(line, "600-normal", 6.6, 27.5, -0.08) for line in motto_lines),
                key=lambda size: float(size[:-2]),
                default="6.6pt",
            ),
            "values_html": _values_html(_values(branding)),
            "values_size": fit(_values(branding), "700-normal", 6.5, 47.0, -0.1),
            "company": company,
            "company_size": fit(company, "700-normal", 6.8, 31.5, -0.06),
            "activity": branding.activity,
            "activity_size": fit(branding.activity, "500-normal", 5.4, 46.0, -0.06),
            "fonts": {
                key: rendering.asset_url(f"fonts/{file}")
                for key, file in {
                    "m400": "montserrat-latin-400-normal.woff",
                    "m400i": "montserrat-latin-400-italic.woff",
                    "m500": "montserrat-latin-500-normal.woff",
                    "m500i": "montserrat-latin-500-italic.woff",
                    "m600": "montserrat-latin-600-normal.woff",
                    "m700": "montserrat-latin-700-normal.woff",
                    "m800": "montserrat-latin-800-normal.woff",
                }.items()
            },
        },
    )


def render(people: Iterable[StaffMember], design: str = "carte") -> bytes:
    organization = require_current_organization()
    return rendering.html_to_pdf(_html(people, design, preview=False), str(organization.pk))


def preview(person: StaffMember, design: str) -> bytes:
    """One card as a PNG (2×), to pick the design on screen."""
    organization = require_current_organization()
    pdf = rendering.html_to_pdf(_html([person], design, preview=True), str(organization.pk))
    pages = rendering.pdf_to_pngs(pdf)
    if design == "carte":  # front (page 1) and back (page 2) side by side
        return _side_by_side(pages)
    return pages[0]


def _side_by_side(pages: list[bytes]) -> bytes:
    import io

    from PIL import Image

    images = [Image.open(io.BytesIO(page)) for page in pages[:2]]
    gap = 40
    card_w = round(images[0].width * 54 / 112)  # each page is 112 mm wide
    canvas = Image.new("RGBA", (card_w * 2 + gap, images[0].height), (0, 0, 0, 0))
    canvas.paste(images[0].crop((0, 0, card_w, images[0].height)), (0, 0))
    offset = round(images[1].width * 58 / 112)
    canvas.paste(images[1].crop((offset, 0, offset + card_w, images[1].height)), (card_w + gap, 0))
    out = io.BytesIO()
    canvas.save(out, "PNG")
    return out.getvalue()
