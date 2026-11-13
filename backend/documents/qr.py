"""QR codes of the tickets (docs/specs/devis-billets.md §7): segno, vector SVG, level Q,
quiet zone of 4 modules. The template sets the printed size (never under 25 mm)."""

from __future__ import annotations

import io


def svg(data: str, *, dark: str = "#000000") -> str:
    import segno  # type: ignore[import-not-found,unused-ignore]

    code = segno.make(data, error="q", micro=False)
    out = io.BytesIO()
    code.save(
        out,
        kind="svg",
        border=4,
        dark=dark,
        light="#FFFFFF",
        xmldecl=False,
        svgns=True,
        omitsize=True,
    )
    return out.getvalue().decode()
