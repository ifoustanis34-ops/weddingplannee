"""Identity of each agency on its documents (docs/specs/devis-billets.md §4 and §2f)."""

from __future__ import annotations

import uuid
from typing import Any

from django.db import models

from core.models import TenantModel


def branding_path(instance: OrganizationBranding, filename: str) -> str:
    """Files of an agency live under its own prefix; the name never comes from the upload."""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"org/{instance.organization_id}/branding/{uuid.uuid4().hex}.{extension}"


def default_activities() -> list[dict[str, str]]:
    return [
        {"label": "Mariages", "icon": "rings"},
        {"label": "Anniversaires", "icon": "cake"},
        {"label": "Soirées privées", "icon": "glass"},
        {"label": "Événements professionnels", "icon": "briefcase"},
    ]


def default_engagements() -> list[dict[str, str]]:
    return [
        {"label": "Qualité du matériel et décoration haut de gamme", "icon": "star"},
        {"label": "Une équipe expérimentée et à votre écoute", "icon": "team"},
        {"label": "Respect des délais et du planning", "icon": "clock"},
        {"label": "Un accompagnement personnalisé", "icon": "heart"},
    ]


def default_scripts() -> dict[str, str]:
    return {
        "satisfaction": "Votre satisfaction est notre plus belle réussite !",
        "detail": "Chaque détail compte…",
        "detail_sub": "Nous créons des instants uniques, à votre image.",
        "priority": "Votre événement, notre priorité !",
        "thanks": "Merci pour votre confiance !",
        "footer": "Ensemble, rendons vos événements uniques !",
    }


def default_keywords() -> list[str]:
    return ["Événements", "Mariages", "Cérémonies", "Entreprises"]


class OrganizationBranding(TenantModel):
    """One per organization, created on first use. Documents copy it into a snapshot."""

    # --- Files (stored under org/{id}/branding/, served by signed URLs) ---
    logo = models.FileField(upload_to=branding_path, blank=True)
    logo_on_dark = models.FileField(upload_to=branding_path, blank=True)
    signature_image = models.FileField(upload_to=branding_path, blank=True)
    stamp_image = models.FileField(upload_to=branding_path, blank=True)
    # Contrast ratio of the logo on the paper and on the dark colour (WCAG), set on upload.
    logo_contrast_light = models.FloatField(null=True, blank=True)
    logo_contrast_dark = models.FloatField(null=True, blank=True)

    # --- Colours ---
    primary_color = models.CharField(max_length=7, blank=True)
    secondary_color = models.CharField(max_length=7, blank=True)
    monogram_color = models.CharField(max_length=7, blank=True)
    use_brand_colors = models.BooleanField(default=False)
    # Default look of the quotes (the quote editor can override both).
    quote_design = models.CharField(max_length=1, default="A")
    quote_palette = models.CharField(max_length=24, default="nuit-or")

    # --- Names and contact details ---
    trade_name = models.CharField(max_length=120, blank=True)
    legal_name = models.CharField(max_length=160, blank=True)
    activity = models.CharField(max_length=80, default="Gestion & organisation d’événements")
    slogan = models.CharField(max_length=60, blank=True)
    address = models.CharField(max_length=200, blank=True)
    phones: models.JSONField[list[str]] = models.JSONField(default=list, blank=True)
    whatsapp = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    website = models.CharField(max_length=120, blank=True)
    socials: models.JSONField[dict[str, str]] = models.JSONField(default=dict, blank=True)

    # --- Legal and payment ---
    tax_ids: models.JSONField[dict[str, str]] = models.JSONField(default=dict, blank=True)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    bank_details = models.TextField(blank=True)
    mobile_money_numbers: models.JSONField[list[dict[str, str]]] = models.JSONField(
        default=list, blank=True
    )

    # --- Texts shown on the documents (§2f) ---
    activities: models.JSONField[list[dict[str, str]]] = models.JSONField(
        default=default_activities, blank=True
    )
    engagements: models.JSONField[list[dict[str, str]]] = models.JSONField(
        default=default_engagements, blank=True
    )
    quote_tagline = models.CharField(
        max_length=110,
        default="Une organisation sur mesure pour faire de votre événement un moment inoubliable.",
        blank=True,
    )
    scripts: models.JSONField[dict[str, str]] = models.JSONField(
        default=default_scripts, blank=True
    )
    signatory = models.CharField(max_length=80, blank=True)
    signatory_role = models.CharField(max_length=60, blank=True)
    footer_keywords: models.JSONField[list[str]] = models.JSONField(
        default=default_keywords, blank=True
    )
    quote_terms = models.TextField(blank=True)
    payment_terms = models.TextField(blank=True)
    footer_text = models.CharField(max_length=200, blank=True)
    show_wedivo_mention = models.BooleanField(default=True)

    class Meta(TenantModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=["organization"], name="one_branding_per_organization"),
            models.CheckConstraint(
                condition=models.Q(vat_rate__isnull=True)
                | models.Q(vat_rate__gte=0, vat_rate__lte=100),
                name="branding_vat_rate_0_100",
            ),
        ]

    def __str__(self) -> str:
        return self.trade_name or str(self.organization_id)

    def file(self, kind: str) -> Any:
        return getattr(self, FILE_FIELDS[kind])


# Upload kinds accepted by POST /organization/branding/files.
FILE_FIELDS = {
    "logo": "logo",
    "logo_on_dark": "logo_on_dark",
    "signature": "signature_image",
    "stamp": "stamp_image",
}


class DocumentTemplate(models.Model):
    """A versioned template (not a tenant table): a document keeps the version it was made with,
    so the design can change without touching what was already sent."""

    class Kind(models.TextChoices):
        QUOTE = "quote", "Devis"
        TICKET = "ticket", "Billet"
        CONTRACT = "contract", "Contrat"
        RECEIPT = "receipt", "Reçu"

    kind = models.CharField(max_length=16, choices=Kind.choices)
    code = models.CharField(max_length=24)  # A, B, C, D for quotes
    name = models.CharField(max_length=60)
    version = models.PositiveSmallIntegerField(default=1)
    path = models.CharField(max_length=120)
    page_size = models.CharField(max_length=24, default="A4")
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["kind", "code", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "code", "version"], name="unique_template_version"
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} {self.code} v{self.version}"


def generated_path(instance: GeneratedDocument, filename: str) -> str:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"org/{instance.organization_id}/documents/{uuid.uuid4().hex}.{extension}"


class GeneratedDocument(TenantModel):
    """A frozen rendering: the data snapshot, the PDF, its first-page PNG and their hash.
    Never regenerated in silence: a change makes a new version."""

    kind = models.CharField(max_length=16, choices=DocumentTemplate.Kind.choices)
    object_id = models.UUIDField()
    version = models.PositiveIntegerField(default=1)
    template = models.ForeignKey(DocumentTemplate, on_delete=models.PROTECT, related_name="+")
    data_snapshot: models.JSONField[dict[str, Any]] = models.JSONField()
    pdf_file = models.FileField(upload_to=generated_path)
    png_file = models.FileField(upload_to=generated_path, blank=True)
    sha256 = models.CharField(max_length=64)
    page_count = models.PositiveSmallIntegerField(default=1)

    class Meta(TenantModel.Meta):
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "kind", "object_id"])]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "kind", "object_id", "version"],
                name="unique_document_version",
            )
        ]
