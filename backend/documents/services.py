"""Agency identity on documents (docs/specs/devis-billets.md §4)."""

from __future__ import annotations

import base64
import mimetypes
from typing import Any, cast

from django.core.files.base import ContentFile
from django.db import transaction

from core.exceptions import BusinessError
from core.signed_files import signed_url
from core.tenant import require_current_organization

from . import images
from .models import FILE_FIELDS, OrganizationBranding

# A logo below this contrast on a background is hard to read there (WCAG large text: 3:1).
MIN_LOGO_CONTRAST = 3.0
UPDATABLE = (
    "primary_color",
    "secondary_color",
    "monogram_color",
    "use_brand_colors",
    "quote_design",
    "quote_palette",
    "trade_name",
    "legal_name",
    "activity",
    "slogan",
    "address",
    "phones",
    "whatsapp",
    "email",
    "website",
    "socials",
    "tax_ids",
    "vat_rate",
    "bank_details",
    "mobile_money_numbers",
    "activities",
    "engagements",
    "quote_tagline",
    "scripts",
    "signatory",
    "signatory_role",
    "footer_keywords",
    "quote_terms",
    "payment_terms",
    "footer_text",
    "show_wedivo_mention",
)


def get_branding() -> OrganizationBranding:
    """The active organization's identity, created on first use from its settings."""
    organization = require_current_organization()
    branding = OrganizationBranding.objects.filter(organization=organization).first()
    if branding is not None:
        return cast(OrganizationBranding, branding)
    with transaction.atomic():
        branding, _ = OrganizationBranding.objects.get_or_create(
            organization=organization,
            defaults={
                "trade_name": organization.name,
                "address": organization.city,
                "quote_terms": organization.legal_mentions,
            },
        )
    return cast(OrganizationBranding, branding)


def current_logo() -> Any:
    """The active organization's logo file (or None), without creating the identity."""
    branding = OrganizationBranding.objects.first()
    return branding.logo if branding is not None and branding.logo else None


def logo_url() -> str | None:
    logo = current_logo()
    return signed_url(logo.name) if logo else None


def logo_data_uri() -> str | None:
    """The logo embedded in a PDF: works with any storage (local disk or S3)."""
    logo = current_logo()
    if not logo:
        return None
    content_type = mimetypes.guess_type(logo.name)[0] or "image/png"
    with logo.open("rb") as handle:
        encoded = base64.b64encode(handle.read()).decode()
    return f"data:{content_type};base64,{encoded}"


def update_branding(branding: OrganizationBranding, data: dict[str, Any]) -> dict[str, Any]:
    changes: dict[str, Any] = {}
    for key in UPDATABLE:
        if key in data and getattr(branding, key) != data[key]:
            changes[key] = {"from": str(getattr(branding, key))[:80], "to": str(data[key])[:80]}
            setattr(branding, key, data[key])
    if changes:
        branding.save()
    return changes


def store_file(branding: OrganizationBranding, kind: str, content: bytes) -> OrganizationBranding:
    """Clean, process and store an identity file; the logo also sets contrast and colours."""
    if kind not in FILE_FIELDS:
        raise BusinessError("invalid", "Type de fichier inconnu.", {"kind": ["Type inconnu."]})
    processed = images.process_upload(content)
    field = branding.file(kind)
    if field:
        field.delete(save=False)
    field.save(f"{kind}.{processed.extension}", ContentFile(processed.content), save=False)
    if kind == "logo":
        branding.logo_contrast_light = processed.contrast_light
        branding.logo_contrast_dark = processed.contrast_dark
        # Colours are proposed from the logo the first time only: they stay editable.
        if processed.colors and not branding.primary_color:
            branding.primary_color = processed.colors[0]
            branding.secondary_color = processed.colors[1] if len(processed.colors) > 1 else ""
    branding.save()
    return branding


def remove_file(branding: OrganizationBranding, kind: str) -> OrganizationBranding:
    if kind not in FILE_FIELDS:
        raise BusinessError("invalid", "Type de fichier inconnu.", {"kind": ["Type inconnu."]})
    field = branding.file(kind)
    if field:
        field.delete(save=False)
    if kind == "logo":
        branding.logo_contrast_light = branding.logo_contrast_dark = None
    branding.save()
    return branding


def monogram(name: str) -> str:
    """Initials shown instead of a missing logo (« Maison Élégance Events » → « ME »)."""
    words = [w for w in name.replace("&", " ").split() if w[:1].isalpha()]
    picked = [words[0], words[1]] if len(words) > 1 else words
    return "".join(w[0].upper() for w in picked) or "W"


def missing_fields(branding: OrganizationBranding) -> list[str]:
    """What a quote would miss (logo, contact details, legal identifiers)."""
    missing = []
    if not branding.logo:
        missing.append("logo")
    if not branding.phones:
        missing.append("phones")
    if not branding.email:
        missing.append("email")
    if not branding.address:
        missing.append("address")
    if not branding.tax_ids:
        missing.append("tax_ids")
    return missing


def warnings(branding: OrganizationBranding) -> list[str]:
    result = []
    if branding.logo and branding.logo_contrast_light is not None:
        if branding.logo_contrast_light < MIN_LOGO_CONTRAST:
            result.append("logo_light")
        if branding.logo_contrast_dark is not None and (
            branding.logo_contrast_dark < MIN_LOGO_CONTRAST and not branding.logo_on_dark
        ):
            result.append("logo_dark")
    return result
