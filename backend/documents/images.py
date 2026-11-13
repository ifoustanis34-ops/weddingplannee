"""Uploaded images of an agency's identity (docs/specs/devis-billets.md §4 and §11).

Pure functions on bytes, so that they are tested without storage:
- the real type is sniffed (never trusted from the extension or the browser);
- SVG files are cleaned (scripts, event handlers, external references removed);
- raster logos are trimmed, made transparent when their background is plain, and resized;
- contrast on the light paper and on the dark colour, and suggested brand colours.
"""

from __future__ import annotations

import colorsys
import io
import re
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

from PIL import Image, ImageOps, UnidentifiedImageError

from core.exceptions import BusinessError

MAX_BYTES = 5 * 1024 * 1024
MAX_SIDE = 1200  # stored master logo, px
PAPER = (255, 255, 255)
DARK = (23, 21, 59)  # darkest ink of the documents (#17153B)
RASTER_FORMATS = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp"}
SVG_NS = "http://www.w3.org/2000/svg"
XLINK = "{http://www.w3.org/1999/xlink}href"
FORBIDDEN_TAGS = {"script", "foreignobject", "iframe", "object", "embed", "audio", "video"}


@dataclass
class ProcessedImage:
    content: bytes
    extension: str
    content_type: str
    contrast_light: float | None = None
    contrast_dark: float | None = None
    colors: list[str] = field(default_factory=list)


def invalid(message: str) -> BusinessError:
    return BusinessError("invalid_file", message, {"file": [message]})


# --- Type sniffing -------------------------------------------------------------------------------


def sniff(content: bytes) -> str:
    """'svg' or a Pillow format name. Refuses anything else, whatever its extension."""
    if len(content) > MAX_BYTES:
        raise invalid("Fichier trop lourd : 5 Mo maximum.")
    head = content[:512].lstrip()
    if head.startswith(b"<?xml") or head.startswith(b"<svg") or b"<svg" in head:
        return "svg"
    try:
        with Image.open(io.BytesIO(content)) as image:
            image.verify()
            fmt = image.format or ""
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise invalid("Choisissez une image PNG, JPG, WEBP ou SVG.") from exc
    if fmt not in RASTER_FORMATS:
        raise invalid("Choisissez une image PNG, JPG, WEBP ou SVG.")
    return fmt


# --- SVG cleaning --------------------------------------------------------------------------------


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def sanitize_svg(content: bytes) -> bytes:
    """Keep the drawing, drop everything that could run code or call the network."""
    text = content.decode("utf-8", errors="replace")
    # Entities and DTDs enable XML bombs and external entity reads: refused outright.
    if re.search(r"<!(DOCTYPE|ENTITY)", text, re.IGNORECASE):
        raise invalid("Ce fichier SVG contient des déclarations interdites.")
    try:
        root = ET.fromstring(text)  # noqa: S314 - DTDs (hence entities) are refused above
    except ET.ParseError as exc:
        raise invalid("Ce fichier SVG est illisible.") from exc
    if _local(root.tag) != "svg":
        raise invalid("Ce fichier n’est pas une image SVG.")

    def clean(element: ET.Element) -> None:
        for child in list(element):
            if _local(child.tag) in FORBIDDEN_TAGS:
                element.remove(child)
                continue
            clean(child)
        for name in list(element.attrib):
            value = element.attrib[name].strip()
            local = _local(name)
            if local.startswith("on"):
                del element.attrib[name]
            elif local == "href" or name == XLINK:
                # Only internal references (#id) and embedded raster images are kept.
                if not (value.startswith("#") or re.match(r"data:image/(png|jpe?g|webp);", value)):
                    del element.attrib[name]
            elif "javascript:" in value.lower() or re.search(r"url\(\s*['\"]?(https?:|//)", value):
                del element.attrib[name]
        if _local(element.tag) == "style" and element.text:
            element.text = re.sub(r"@import[^;]+;|url\([^)]*\)", "", element.text)

    clean(root)
    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    return bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True))


def svg_colors(content: bytes) -> list[str]:
    """Hex colours used by an SVG drawing, most frequent first (for brand suggestions)."""
    found = re.findall(r"#([0-9a-fA-F]{6})\b", content.decode("utf-8", errors="ignore"))
    counts: dict[str, int] = {}
    for value in found:
        key = f"#{value.upper()}"
        counts[key] = counts.get(key, 0) + 1
    return [c for c, _ in sorted(counts.items(), key=lambda item: -item[1]) if _is_brand(c)][:2]


# --- Raster processing ---------------------------------------------------------------------------


def _plain_background(image: Image.Image) -> tuple[int, int, int] | None:
    """The background colour when the four corners agree, else None."""
    rgb = image.convert("RGB")
    w, h = rgb.size
    corners = [rgb.getpixel(p) for p in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))]
    reference = corners[0]
    if all(max(abs(a - b) for a, b in zip(c, reference, strict=True)) <= 12 for c in corners):  # type: ignore[arg-type]
        return reference  # type: ignore[return-value]
    return None


def make_transparent(image: Image.Image, background: tuple[int, int, int]) -> Image.Image:
    """Alpha grows with the distance to the background colour (soft, anti-aliased edges)."""
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    assert pixels is not None
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]  # type: ignore[misc]
            distance = max(abs(r - background[0]), abs(g - background[1]), abs(b - background[2]))
            alpha = min(255, distance * 4)
            pixels[x, y] = (r, g, b, min(a, alpha))
    return rgba


def trim(image: Image.Image, margin: float = 0.02) -> Image.Image:
    """Crop to the visible drawing, keeping a small margin."""
    bbox = image.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if bbox is None:
        raise invalid("L’image est vide.")
    cropped = image.crop(bbox)
    pad = max(1, round(max(cropped.size) * margin))
    canvas = Image.new("RGBA", (cropped.width + 2 * pad, cropped.height + 2 * pad), (0, 0, 0, 0))
    canvas.paste(cropped, (pad, pad))
    return canvas


def _luminance(rgb: tuple[float, float, float]) -> float:
    def channel(value: float) -> float:
        v = value / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    la, lb = _luminance(a), _luminance(b)
    light, dark = max(la, lb), min(la, lb)
    return round((light + 0.05) / (dark + 0.05), 2)


def _opaque_pixels(image: Image.Image) -> list[tuple[int, int, int]]:
    small = image.copy()
    small.thumbnail((96, 96))
    return [(r, g, b) for r, g, b, a in small.get_flattened_data() if a > 128]  # type: ignore[misc]


def logo_contrast(image: Image.Image) -> tuple[float | None, float | None]:
    """Contrast of the logo's average ink on the paper and on the dark colour."""
    pixels = _opaque_pixels(image)
    if not pixels:
        return None, None
    n = len(pixels)
    mean = (
        sum(p[0] for p in pixels) / n,
        sum(p[1] for p in pixels) / n,
        sum(p[2] for p in pixels) / n,
    )
    return contrast_ratio(mean, PAPER), contrast_ratio(mean, DARK)


def _is_brand(hex_color: str) -> bool:
    r, g, b = (int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5))
    _, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
    return saturation > 0.25 and 0.12 < lightness < 0.85


def dominant_colors(image: Image.Image) -> list[str]:
    """Up to two saturated colours of the logo, most present first (greys, white, black skipped)."""
    pixels = _opaque_pixels(image)
    if not pixels:
        return []
    sample = Image.new("RGB", (len(pixels), 1))
    sample.putdata(pixels)
    palette = sample.quantize(colors=8)
    colors = palette.getpalette() or []
    counts = sorted(palette.getcolors() or [], reverse=True)
    result: list[str] = []
    for _, index in counts:
        start = int(index) * 3  # type: ignore[call-overload]
        r, g, b = colors[start : start + 3]
        hex_color = f"#{r:02X}{g:02X}{b:02X}"
        if _is_brand(hex_color) and all(_distance(hex_color, c) > 60 for c in result):
            result.append(hex_color)
        if len(result) == 2:
            break
    return result


def _distance(a: str, b: str) -> int:
    return max(abs(int(a[i : i + 2], 16) - int(b[i : i + 2], 16)) for i in (1, 3, 5))


def process_raster(content: bytes, *, transparent: bool) -> ProcessedImage:
    """Logo, signature or stamp: transparent if the background is plain, trimmed, ≤ 1200 px PNG."""
    with Image.open(io.BytesIO(content)) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGBA")
    # Resize first: the transparency pass walks every pixel.
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    if transparent:
        background = _plain_background(image)
        if background is not None:
            image = make_transparent(image, background)
        image = trim(image)
    light, dark = logo_contrast(image)
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return ProcessedImage(
        content=output.getvalue(),
        extension="png",
        content_type="image/png",
        contrast_light=light,
        contrast_dark=dark,
        colors=dominant_colors(image),
    )


def process_upload(content: bytes) -> ProcessedImage:
    kind = sniff(content)
    if kind == "svg":
        cleaned = sanitize_svg(content)
        return ProcessedImage(
            content=cleaned,
            extension="svg",
            content_type="image/svg+xml",
            colors=svg_colors(cleaned),
        )
    return process_raster(content, transparent=True)
