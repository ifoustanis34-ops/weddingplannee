from __future__ import annotations

import re
from typing import Any

from rest_framework import serializers

from core.signed_files import signed_url

from . import services
from .models import FILE_FIELDS, GeneratedDocument, OrganizationBranding

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
ICONS = {
    "rings",
    "cake",
    "glass",
    "briefcase",
    "star",
    "team",
    "clock",
    "heart",
    "flower",
    "camera",
    "music",
    "gift",
    "car",
    "calendar",
    "shield",
    "sparkles",
}


def _items(value: Any, max_items: int, max_length: int) -> list[dict[str, str]]:
    if not isinstance(value, list) or len(value) > max_items:
        raise serializers.ValidationError(f"{max_items} éléments au maximum.")
    cleaned = []
    for item in value:
        label = str((item or {}).get("label", "")).strip()
        icon = str((item or {}).get("icon", "star"))
        if not label or len(label) > max_length:
            raise serializers.ValidationError(f"Chaque texte fait de 1 à {max_length} caractères.")
        cleaned.append({"label": label, "icon": icon if icon in ICONS else "star"})
    return cleaned


class BrandingSerializer(serializers.ModelSerializer[OrganizationBranding]):
    files = serializers.SerializerMethodField()
    monogram = serializers.SerializerMethodField()
    missing = serializers.SerializerMethodField()
    warnings = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationBranding
        fields = [
            *services.UPDATABLE,
            "logo_contrast_light",
            "logo_contrast_dark",
            "files",
            "monogram",
            "missing",
            "warnings",
            "updated_at",
        ]
        read_only_fields = ["logo_contrast_light", "logo_contrast_dark", "updated_at"]

    def get_files(self, branding: OrganizationBranding) -> dict[str, str | None]:
        return {kind: signed_url(branding.file(kind).name or None) for kind in FILE_FIELDS}

    def get_monogram(self, branding: OrganizationBranding) -> str:
        return services.monogram(branding.trade_name or branding.organization.name)

    def get_missing(self, branding: OrganizationBranding) -> list[str]:
        return services.missing_fields(branding)

    def get_warnings(self, branding: OrganizationBranding) -> list[str]:
        return services.warnings(branding)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        for key in ("primary_color", "secondary_color", "monogram_color"):
            value = attrs.get(key)
            if value and not HEX.match(value):
                raise serializers.ValidationError({key: ["Couleur au format #RRGGBB."]})
            if value:
                attrs[key] = value.upper()
        return attrs

    def validate_quote_design(self, value: str) -> str:
        from .quote_document import TEMPLATES

        if value not in TEMPLATES:
            raise serializers.ValidationError("Modèle inconnu.")
        return value

    def validate_quote_palette(self, value: str) -> str:
        from .palettes import PALETTES

        if value not in PALETTES:
            raise serializers.ValidationError("Palette inconnue.")
        return value

    def validate_activities(self, value: Any) -> list[dict[str, str]]:
        return _items(value, 4, 40)

    def validate_engagements(self, value: Any) -> list[dict[str, str]]:
        return _items(value, 4, 70)

    def validate_phones(self, value: Any) -> list[str]:
        if not isinstance(value, list) or len(value) > 3:
            raise serializers.ValidationError("3 numéros au maximum.")
        return [str(v).strip()[:32] for v in value if str(v).strip()]

    def validate_scripts(self, value: Any) -> dict[str, str]:
        defaults = OrganizationBranding._meta.get_field("scripts").get_default()
        if not isinstance(value, dict):
            raise serializers.ValidationError("Textes invalides.")
        cleaned = {}
        for key in defaults:
            text = str(value.get(key, defaults[key])).strip()
            if len(text) > 70:
                raise serializers.ValidationError({key: ["70 caractères au maximum."]})
            cleaned[key] = text
        return cleaned

    def validate_socials(self, value: Any) -> dict[str, str]:
        allowed = {"facebook", "instagram", "tiktok", "whatsapp", "linkedin", "youtube"}
        if not isinstance(value, dict):
            raise serializers.ValidationError("Réseaux invalides.")
        return {k: str(v).strip()[:60] for k, v in value.items() if k in allowed and str(v).strip()}

    def validate_footer_keywords(self, value: Any) -> list[str]:
        if not isinstance(value, list) or len(value) > 5:
            raise serializers.ValidationError("5 mots-clés au maximum.")
        return [str(v).strip()[:20] for v in value if str(v).strip()]

    def validate_tax_ids(self, value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            raise serializers.ValidationError("Identifiants invalides.")
        allowed = {"rccm", "nif", "ncc", "niu", "ninea", "ifu"}
        return {k: str(v).strip()[:40] for k, v in value.items() if k in allowed and str(v).strip()}

    def validate_mobile_money_numbers(self, value: Any) -> list[dict[str, str]]:
        if not isinstance(value, list) or len(value) > 4:
            raise serializers.ValidationError("4 numéros au maximum.")
        return [
            {"provider": str(v.get("provider", ""))[:20], "number": str(v.get("number", ""))[:32]}
            for v in value
            if isinstance(v, dict) and str(v.get("number", "")).strip()
        ]


class BrandingFileSerializer(serializers.Serializer[Any]):
    kind = serializers.ChoiceField(choices=list(FILE_FIELDS))
    file = serializers.FileField()


class GeneratedDocumentSerializer(serializers.ModelSerializer[GeneratedDocument]):
    pdf_url = serializers.SerializerMethodField()
    png_url = serializers.SerializerMethodField()
    template = serializers.CharField(source="template.code", read_only=True)

    class Meta:
        model = GeneratedDocument
        fields = [
            "id",
            "kind",
            "version",
            "template",
            "sha256",
            "page_count",
            "pdf_url",
            "png_url",
            "created_at",
        ]

    def get_pdf_url(self, document: GeneratedDocument) -> str | None:
        return signed_url(document.pdf_file.name or None)

    def get_png_url(self, document: GeneratedDocument) -> str | None:
        return signed_url(document.png_file.name or None)


class PreviewSerializer(serializers.Serializer[Any]):
    """POST /documents/preview: the editor's data (or a saved quote), rendered as a PNG."""

    kind = serializers.ChoiceField(choices=["quote"])
    quote = serializers.UUIDField(required=False, allow_null=True)
    draft = serializers.DictField(required=False, default=dict)
