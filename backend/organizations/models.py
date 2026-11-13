from __future__ import annotations

import uuid
from datetime import datetime

from django.core.validators import FileExtensionValidator
from django.db import models


class Organization(models.Model):
    """A wedding planning company: the root of every tenant (not tenant-scoped itself)."""

    class Currency(models.TextChoices):
        XOF = "XOF", "Franc CFA (UEMOA)"
        XAF = "XAF", "Franc CFA (CEMAC)"
        EUR = "EUR", "Euro"

    class Plan(models.TextChoices):
        ESSENTIEL = "essentiel", "Essentiel"
        PRO = "pro", "Pro"
        AGENCE = "agence", "Agence"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=32, unique=True)
    name = models.CharField(max_length=120)
    logo = models.FileField(
        upload_to="logos/",
        blank=True,
        validators=[FileExtensionValidator(["png", "jpg", "jpeg", "svg", "webp"])],
    )
    country = models.CharField(max_length=2, help_text="Code ISO 3166-1 alpha-2, ex. CI")
    city = models.CharField(max_length=80)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.XOF)
    timezone = models.CharField(max_length=64, default="Africa/Abidjan")
    weddings_per_year = models.PositiveSmallIntegerField(null=True, blank=True)
    # Daily email of the open alerts to the owner (reservations-stock.md §5.4).
    alert_digest = models.BooleanField(default=True)
    # Cancellation policy (reservations-stock.md §4.1): the deposit is kept by the agency.
    deposit_kept_on_cancel = models.BooleanField(default=True)
    # « Mariages » module (feedback 13/11/2026): weddings, their tasks, tickets and guests,
    # suppliers on weddings. Off by default, turned on at signup or in Paramètres › Entreprise.
    weddings_enabled = models.BooleanField(default=False)
    plan = models.CharField(max_length=16, choices=Plan.choices, default=Plan.PRO)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    quote_prefix = models.CharField(max_length=8, default="DV")
    quote_validity_days = models.PositiveSmallIntegerField(default=30)
    legal_mentions = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def is_in_trial(self, now: datetime) -> bool:
        return self.trial_ends_at is not None and now < self.trial_ends_at


class DocumentSequence(models.Model):
    """Per-organization, per-year counter for document numbers (DV-2026-0048, CT-2026-0003).

    Incremented under a row lock (SELECT ... FOR UPDATE): concurrent quotes never share a number.
    Lives under RLS like business tables (see migration).
    """

    class Kind(models.TextChoices):
        QUOTE = "quote", "Devis"
        CONTRACT = "contract", "Contrat"
        RECEIPT = "receipt", "Reçu"
        RESERVATION = "reservation", "Réservation"
        INVOICE = "invoice", "Facture"
        CREDIT_NOTE = "credit_note", "Avoir"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="+")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    year = models.PositiveSmallIntegerField()
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "kind", "year"], name="unique_document_sequence"
            )
        ]

    def __str__(self) -> str:
        return f"{self.kind} {self.year}: {self.last_number}"


class SubscriptionPlan(models.Model):
    """Offer catalogue (Essentiel, Pro, Agence): prices live in the database, never in code.

    Shared by every organization (not tenant-scoped); ``code`` matches ``Organization.plan``.
    """

    code = models.CharField(max_length=16, unique=True, choices=Organization.Plan.choices)
    name = models.CharField(max_length=40)
    description = models.CharField(max_length=160)
    monthly_price = models.BigIntegerField(help_text="FCFA par mois")
    max_users = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Vide : illimité")
    modules = models.JSONField(default=list, blank=True)
    features = models.JSONField(default=list, blank=True, help_text="Points affichés aux clients")
    position = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["position", "monthly_price"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monthly_price__gte=0), name="plan_price_not_negative"
            )
        ]

    def __str__(self) -> str:
        return self.name
