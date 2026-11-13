from __future__ import annotations

import secrets
import uuid
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from catalog.models import Unit
from core.models import TenantModel


def new_public_token() -> str:
    """Unguessable token for the public quote link (CLAUDE.md §11)."""
    return secrets.token_urlsafe(32)


PERCENT = [MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))]


class Quote(TenantModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        SENT = "sent", "Envoyé"
        ACCEPTED = "accepted", "Accepté"
        REFUSED = "refused", "Refusé"
        EXPIRED = "expired", "Expiré"

    number = models.CharField(max_length=32, blank=True)
    client = models.ForeignKey(
        "crm.Client", on_delete=models.PROTECT, null=True, blank=True, related_name="quotes"
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    issue_date = models.DateField()
    valid_until = models.DateField()
    wedding_date = models.DateField(null=True, blank=True)
    guest_count = models.PositiveIntegerField(null=True, blank=True)
    discount_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0"), validators=PERCENT
    )
    deposit_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("30"), validators=PERCENT
    )
    payment_terms = models.TextField(blank=True)
    # --- Document (docs/specs/devis-billets.md §2b, §2f); blank = the agency's default ---
    design = models.CharField(max_length=1, blank=True)  # A, B, C or D
    palette = models.CharField(max_length=24, blank=True)
    tagline = models.CharField(max_length=140, blank=True)
    event_type = models.CharField(max_length=40, default="Mariage")
    venue = models.CharField(max_length=160, blank=True)
    notes = models.TextField(blank=True)
    # Amounts in FCFA (integers), always recomputed by the server.
    subtotal = models.BigIntegerField(default=0)
    discount_amount = models.BigIntegerField(default=0)
    total = models.BigIntegerField(default=0)
    deposit_amount = models.BigIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    refused_at = models.DateTimeField(null=True, blank=True)
    refusal_reason = models.TextField(blank=True)
    pdf_file = models.FileField(upload_to="quotes/", blank=True)
    public_token = models.CharField(max_length=64, unique=True, default=new_public_token)
    is_template = models.BooleanField(default=False)
    template_name = models.CharField(max_length=120, blank=True)

    class Meta(TenantModel.Meta):
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "is_template"]),
            models.Index(fields=["organization", "valid_until"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "number"],
                condition=~models.Q(number=""),
                name="unique_quote_number_per_org",
            ),
            models.CheckConstraint(
                condition=models.Q(discount_pct__gte=0, discount_pct__lte=100)
                & models.Q(deposit_pct__gte=0, deposit_pct__lte=100),
                name="quote_percentages_range",
            ),
            models.CheckConstraint(
                condition=models.Q(subtotal__gte=0, total__gte=0, deposit_amount__gte=0),
                name="quote_amounts_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(is_template=True) | models.Q(client__isnull=False),
                name="quote_has_client_unless_template",
            ),
        ]

    def __str__(self) -> str:
        return self.number or self.template_name or str(self.pk)


class QuoteLine(TenantModel):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="lines")
    service_item = models.ForeignKey(
        "catalog.ServiceItem", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    label = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=16, choices=Unit.choices, default=Unit.FLAT)
    unit_price = models.BigIntegerField()
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1"))
    amount = models.BigIntegerField(default=0)
    position = models.PositiveSmallIntegerField(default=0)
    icon = models.CharField(max_length=24, blank=True)

    class Meta(TenantModel.Meta):
        ordering = ["position"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(unit_price__gte=0, quantity__gt=0, amount__gte=0),
                name="quote_line_values_positive",
            )
        ]

    def __str__(self) -> str:
        return self.label


def partner_path(instance: QuotePartner, filename: str) -> str:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"org/{instance.organization_id}/partners/{uuid.uuid4().hex}.{extension}"


class QuotePartner(TenantModel):
    """« En partenariat avec … » (docs/specs/devis-billets.md §2d): an external partner, typed
    by the agency and visible only in its organization. At most two per quote."""

    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="partners")
    name = models.CharField(max_length=120)
    activity = models.CharField(max_length=120, blank=True)
    signatory = models.CharField(max_length=80, blank=True)
    signatory_role = models.CharField(max_length=60, blank=True)
    logo = models.FileField(upload_to=partner_path, blank=True)
    signature_image = models.FileField(upload_to=partner_path, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta(TenantModel.Meta):
        ordering = ["position"]
