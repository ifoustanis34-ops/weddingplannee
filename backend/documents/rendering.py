"""One rendering per document: HTML/CSS template → PDF (WeasyPrint) → PNG (pypdfium2).

docs/specs/devis-billets.md §3. The screen preview, the downloaded PDF and the email image all
come from here, so that they are identical.
"""

from __future__ import annotations

import hashlib
import io
import json
import mimetypes
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.core.cache import cache
from django.core.files.storage import default_storage
from django.template.loader import render_to_string

DOCUMENTS_DIR = Path(__file__).resolve().parent
ASSET_SCHEME = "wedivo-asset:"  # fonts and decorations of the templates
FILE_SCHEME = "wedivo-file:"  # files of the organization (logo, signature, photos…)
PREVIEW_TTL = 600  # seconds (§3: 10 minutes)
SCREEN_SCALE = 2.0  # PNG at 2× (≈ 192 dpi) for the screen and the emails
PRINT_SCALE = 300 / 72


class BlockedResource(Exception):
    pass


def asset_url(path: str) -> str:
    return f"{ASSET_SCHEME}{path}"


def file_url(name: str | None) -> str | None:
    return f"{FILE_SCHEME}{name}" if name else None


def _fetcher(organization_id: str) -> Any:
    """WeasyPrint may only read the template's resources and the organization's own files:
    no network request, no file of another agency (§3, §11)."""
    from weasyprint.urls import URLFetcher, URLFetcherResponse

    prefix = f"org/{organization_id}/"

    class DocumentFetcher(URLFetcher):  # type: ignore[misc]
        def fetch(self, url: str, headers: Any = None) -> Any:
            if url.startswith("data:"):
                return super().fetch(url, headers)
            if url.startswith(ASSET_SCHEME):
                path = (DOCUMENTS_DIR / url[len(ASSET_SCHEME) :]).resolve()
                if not path.is_relative_to(DOCUMENTS_DIR) or not path.is_file():
                    raise BlockedResource(url)
                body = path.read_bytes()
                name = path.name
            elif url.startswith(FILE_SCHEME):
                name = url[len(FILE_SCHEME) :]
                if ".." in name or not name.startswith(prefix) or not default_storage.exists(name):
                    raise BlockedResource(url)
                with default_storage.open(name, "rb") as handle:
                    body = handle.read()
            else:
                raise BlockedResource(url)
            mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
            if name.endswith(".woff"):
                mime = "font/woff"
            return URLFetcherResponse(url, body=body, headers={"Content-Type": mime})

    return DocumentFetcher()


@dataclass
class Rendering:
    pdf: bytes
    pages: list[bytes]  # one PNG per page

    @property
    def page_count(self) -> int:
        return len(self.pages)


_local = threading.local()


def _font_config() -> Any:
    """One font configuration per thread: the embedded fonts are loaded once, not per page."""
    from weasyprint.text.fonts import FontConfiguration

    if not hasattr(_local, "fonts"):
        _local.fonts = FontConfiguration()
    return _local.fonts


def html_to_pdf(html: str, organization_id: str) -> bytes:
    from weasyprint import HTML

    document = HTML(string=html, base_url=str(DOCUMENTS_DIR), url_fetcher=_fetcher(organization_id))
    pdf: bytes = document.write_pdf(font_config=_font_config())
    return pdf


def pdf_to_pngs(pdf: bytes, scale: float = SCREEN_SCALE) -> list[bytes]:
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(pdf)
    pages = []
    try:
        for index in range(len(document)):
            image = document[index].render(scale=scale).to_pil()
            out = io.BytesIO()
            image.save(out, format="PNG", compress_level=6)  # optimize: much slower, ~same size
            pages.append(out.getvalue())
    finally:
        document.close()
    return pages


def stack(pages: list[bytes], gap: int = 24) -> bytes:
    """All pages one under the other, for the editor preview."""
    from PIL import Image

    if len(pages) == 1:
        return pages[0]
    images = [Image.open(io.BytesIO(page)).convert("RGB") for page in pages]
    width = max(image.width for image in images)
    height = sum(image.height for image in images) + gap * (len(images) - 1)
    sheet = Image.new("RGB", (width, height), (229, 226, 240))
    y = 0
    for image in images:
        sheet.paste(image, (0, y))
        y += image.height + gap
    out = io.BytesIO()
    sheet.save(out, format="PNG", compress_level=6)
    return out.getvalue()


def render(template: str, context: dict[str, Any], organization_id: str) -> Rendering:
    """Render; a document longer than one page is rendered again with its page numbers."""
    html = render_to_string(template, {**context, "multipage": False})
    pdf = html_to_pdf(html, organization_id)
    pages = pdf_to_pngs(pdf)
    if len(pages) > 1:
        html = render_to_string(template, {**context, "multipage": True})
        pdf = html_to_pdf(html, organization_id)
        pages = pdf_to_pngs(pdf)
    return Rendering(pdf=pdf, pages=pages)


def fingerprint(data: Any) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str, ensure_ascii=False).encode()
    ).hexdigest()


def cached_preview(
    organization_id: str, kind: str, snapshot: dict[str, Any], build: Any
) -> tuple[bytes, int]:
    """PNG of all pages, cached by fingerprint of the data (`org:{id}:` prefix, §3)."""
    key = f"org:{organization_id}:preview:{kind}:{fingerprint(snapshot)}"
    hit = cache.get(key)
    if hit is not None:
        return hit["png"], hit["pages"]
    rendering: Rendering = build()
    png = stack(rendering.pages)
    cache.set(key, {"png": png, "pages": rendering.page_count}, PREVIEW_TTL)
    return png, rendering.page_count
