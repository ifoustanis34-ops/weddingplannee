"""Visual fidelity of the quote templates (docs/specs/devis-billets.md §12).

The sample quote (donnees-exemple.json) is rendered with each design, then compared with the
reference image zone by zone (SSIM). The reference pages are 2:3 and the documents A4 (decision
of R1): the reference is scaled to the A4 page before comparison. Photos are crops of the
reference images (test only, §2c); the reference logo is not an agency file, so the logo zone is
left out.

Requires numpy (dev dependency).
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.conf import settings
from PIL import Image, ImageFilter

from . import generation, rendering, samples

REFERENCE_DIR = Path(settings.BASE_DIR).parent / "devis"
REFERENCES = {
    "A": "devis-A-prestige.jpg",
    "B": "devis-B-elegance.jpg",
    "C": "devis-C-classique.jpg",
    "D": "devis-D-partenariat.jpg",
}
# Page area of the D screenshot (phone capture with margins), in pixels.
D_PAGE = (18, 193, 480, 888)
COMPARE_WIDTH = 720  # reference resolution
THRESHOLD = 0.90
# Composition level: zones reduced 4 times then blurred, so that block positions, sizes,
# colours and masses are compared, not glyphs (fonts, icons and wording of the references
# cannot be reproduced exactly: AI-drawn lettering, wrong totals corrected on purpose, §2e).
LAYOUT_FACTOR = 4


@dataclass(frozen=True)
class Zone:
    name: str
    box: tuple[float, float, float, float]  # x, y, width, height in mm on the A4 page


# Zones without photo nor logo (§12: only they are comparable), in A4 millimetres.
ZONES: dict[str, list[Zone]] = {
    "A": [
        Zone("titre", (6, 44, 112, 22)),
        Zone("informations", (6, 70, 198, 23)),
        Zone("tableau", (6, 97, 146, 108)),
        Zone("pourquoi", (156, 97, 48, 110)),
        Zone("totaux", (6, 208, 146, 36)),
        Zone("conditions", (6, 246, 198, 29)),
        Zone("pied", (0, 278, 210, 19)),
    ],
    "B": [
        Zone("colonne", (6, 48, 49, 110)),
        Zone("tableau", (61, 55, 144, 114)),
        Zone("totaux", (61, 173, 144, 39)),
        Zone("cartes", (61, 218, 144, 39)),
        Zone("engagements", (6, 258, 198, 12)),
        Zone("pied", (0, 275, 210, 22)),
    ],
    "C": [
        Zone("titre", (11, 44, 56, 34)),
        Zone("informations", (71, 44, 129, 37)),
        Zone("tableau", (11, 85, 189, 93)),
        Zone("totaux", (112, 181, 88, 38)),
        Zone("engagements", (11, 222, 189, 18)),
        Zone("conditions", (11, 243, 189, 28)),
        Zone("pied", (0, 276, 210, 21)),
    ],
    "D": [
        Zone("titre", (9, 46, 60, 30)),
        Zone("informations", (72, 46, 129, 32)),
        Zone("tableau", (9, 80, 192, 68)),
        Zone("totaux", (104, 152, 97, 30)),
        Zone("modalites", (104, 185, 97, 27)),
        Zone("conditions", (9, 216, 192, 33)),
        Zone("pied", (0, 270, 210, 27)),
    ],
}
# Photo areas of the reference images (fractions of the page) injected into the sample.
PHOTOS: dict[str, dict[str, tuple[float, float, float, float]]] = {
    "A": {"hero": (0.6, 0.0, 1.0, 0.25)},
    "B": {"hero": (0.42, 0.0, 0.78, 0.16), "side": (0.0, 0.53, 0.25, 0.92)},
    "C": {"hero": (0.53, 0.0, 1.0, 0.14), "side": (0.05, 0.61, 0.52, 0.74)},
    "D": {"hero": (0.69, 0.0, 1.0, 0.19), "side": (0.04, 0.55, 0.47, 0.74)},
}


def reference(design: str) -> Image.Image:
    image = Image.open(REFERENCE_DIR / REFERENCES[design]).convert("RGB")
    if design == "D":
        image = image.crop(D_PAGE)
    return image


def _data_uri(image: Image.Image) -> str:
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=92)
    return "data:image/jpeg;base64," + base64.b64encode(out.getvalue()).decode()


def sample_with_photos(design: str) -> dict[str, Any]:
    snapshot = samples.quote_snapshot(design)
    page = reference(design)
    for slot, (left, top, right, bottom) in PHOTOS[design].items():
        crop = page.crop(
            (
                int(left * page.width),
                int(top * page.height),
                int(right * page.width),
                int(bottom * page.height),
            )
        )
        snapshot["photos"][slot] = _data_uri(crop)
    return snapshot


def _gray(image: Image.Image, blur: float = 1.2) -> Any:
    import numpy as np

    return np.asarray(image.convert("L").filter(ImageFilter.GaussianBlur(blur)), dtype=np.float64)


def _box_filter(values: Any, size: int = 7) -> Any:
    import numpy as np

    padded = np.pad(values, size // 2, mode="edge")
    summed = padded.cumsum(0).cumsum(1)
    summed = np.pad(summed, ((1, 0), (1, 0)))
    return (
        summed[size:, size:]
        - summed[:-size, size:]
        - summed[size:, :-size]
        + summed[:-size, :-size]
    ) / (size * size)


def ssim(a: Image.Image, b: Image.Image, blur: float = 1.2) -> tuple[float, Any]:
    """Mean structural similarity and its map (Wang et al. 2004, 7 × 7 window)."""
    x, y = _gray(a, blur), _gray(b, blur)
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    mx, my = _box_filter(x), _box_filter(y)
    sxx = _box_filter(x * x) - mx * mx
    syy = _box_filter(y * y) - my * my
    sxy = _box_filter(x * y) - mx * my
    index = ((2 * mx * my + c1) * (2 * sxy + c2)) / ((mx * mx + my * my + c1) * (sxx + syy + c2))
    return float(index.mean()), index


def layout_ssim(a: Image.Image, b: Image.Image) -> float:
    size = (max(8, a.width // LAYOUT_FACTOR), max(8, a.height // LAYOUT_FACTOR))
    small_a = a.resize(size, Image.Resampling.BOX)
    small_b = b.resize(size, Image.Resampling.BOX)
    return ssim(small_a, small_b, blur=1.5)[0]


@dataclass
class Report:
    design: str
    scores: dict[str, float]
    layout: dict[str, float]
    rendered: Image.Image
    reference: Image.Image
    maps: dict[str, Any]

    @property
    def minimum(self) -> float:
        return min(self.scores.values())

    @property
    def layout_minimum(self) -> float:
        return min(self.layout.values())


def compare(design: str) -> Report:
    rendering = generation.render(sample_with_photos(design))
    rendered = Image.open(io.BytesIO(rendering.pages[0])).convert("RGB")
    height = round(COMPARE_WIDTH * 297 / 210)
    rendered = rendered.resize((COMPARE_WIDTH, height), Image.Resampling.LANCZOS)
    ref = reference(design).resize((COMPARE_WIDTH, height), Image.Resampling.LANCZOS)
    scale = COMPARE_WIDTH / 210
    scores, layout, maps = {}, {}, {}
    for zone in ZONES[design]:
        x, y, w, h = (round(v * scale) for v in zone.box)
        box = (x, y, x + w, y + h)
        scores[zone.name], maps[zone.name] = ssim(rendered.crop(box), ref.crop(box))
        layout[zone.name] = layout_ssim(rendered.crop(box), ref.crop(box))
    return Report(design, scores, layout, rendered, ref, maps)


def save_diff(report: Report, directory: Path) -> Path:
    """Side by side (rendering | reference | difference map) in docs/rendus/diff/."""
    import numpy as np
    from PIL import ImageChops

    directory.mkdir(parents=True, exist_ok=True)
    width, height = report.rendered.size
    difference = ImageChops.difference(report.rendered, report.reference).convert("L")
    difference = Image.fromarray(np.clip(np.asarray(difference) * 3, 0, 255).astype("uint8"))
    sheet = Image.new("RGB", (width * 3 + 40, height), "white")
    sheet.paste(report.rendered, (0, 0))
    sheet.paste(report.reference, (width + 20, 0))
    sheet.paste(difference.convert("RGB"), (2 * width + 40, 0))
    name = report.design if report.design.startswith("billet-") else f"devis-{report.design}"
    path = directory / f"{name}.png"
    sheet.save(path, optimize=True)
    return path


# --- Tickets (billets/, 1080 × 720 px; the ticket spans x 8 → 1062, y 45 → 668) -------------------

TICKET_DIR = Path(settings.BASE_DIR).parent / "billets"
TICKET_REFERENCES = {
    "or-noir": "billet-or-noir.jpg",
    "bleu-royal": "billet-bleu-royal.jpg",
    "emeraude": "billet-emeraude.jpg",
}
TICKET_AREA = (8, 45, 1062, 668)
TICKET_WIDTH = 1054
# Zones without photo, in millimetres of the 200 × 118 mm ticket.
TICKET_ZONES = [
    Zone("titre", (50, 6, 89, 12)),
    Zone("prenoms", (50, 30, 89, 38)),
    Zone("colonnes", (53, 71, 85, 22)),
    Zone("talon-haut", (141, 1, 57, 18)),
    Zone("talon-carte", (143, 63, 47, 32)),
    Zone("talon-bas", (141, 104, 57, 13)),
]


def compare_ticket(variant: str) -> Report:
    from . import ticket_document

    snapshot = samples.ticket_snapshot(variant)
    result = rendering.render(
        ticket_document.TEMPLATE, ticket_document.context(snapshot), snapshot["organization_id"]
    )
    height = round(TICKET_WIDTH * 118 / 200)
    rendered = Image.open(io.BytesIO(result.pages[0])).convert("RGB")
    rendered = rendered.resize((TICKET_WIDTH, height), Image.Resampling.LANCZOS)
    ref = Image.open(TICKET_DIR / TICKET_REFERENCES[variant]).convert("RGB").crop(TICKET_AREA)
    ref = ref.resize((TICKET_WIDTH, height), Image.Resampling.LANCZOS)
    scale = TICKET_WIDTH / 200
    scores, layout, maps = {}, {}, {}
    for zone in TICKET_ZONES:
        x, y, w, h = (round(v * scale) for v in zone.box)
        box = (x, y, x + w, y + h)
        scores[zone.name], maps[zone.name] = ssim(rendered.crop(box), ref.crop(box))
        layout[zone.name] = layout_ssim(rendered.crop(box), ref.crop(box))
    return Report(f"billet-{variant}", scores, layout, rendered, ref, maps)
