"""Supplier directory (« Fournisseurs », renamed from « Prestataires » on 13/11/2026) and their
work on weddings (CLAUDE.md §7.7, complement §13)."""

from __future__ import annotations

from django.db import models

from core.models import TenantModel


class Vendor(TenantModel):
    class Kind(models.TextChoices):
        # Feedback 13/11/2026: one address book, two kinds. A supplier sells to the agency
        # (flowers, catering, cake…); a partner works with it or completes its equipment.
        SUPPLIER = "supplier", "Fournisseur"
        PARTNER = "partner", "Partenaire"

    class Category(models.TextChoices):
        DECORATION = "decoration", "Décoration"
        CATERER = "caterer", "Traiteur"
        PHOTOGRAPHER = "photographer", "Photographe"
        VIDEOGRAPHER = "videographer", "Vidéaste"
        DJ = "dj", "DJ"
        VENUE = "venue", "Salle"
        CAKE = "cake", "Gâteau"
        RENTAL = "rental", "Location de matériel"
        TRANSPORT = "transport", "Transport"
        FLOWERS = "flowers", "Fleuriste"
        SOUND = "sound", "Sonorisation et lumière"
        SUPPLIES = "supplies", "Fournitures et consommables"
        SECURITY = "security", "Sécurité"
        OTHER = "other", "Autre"

    name = models.CharField(max_length=160)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.SUPPLIER)
    category = models.CharField(max_length=16, choices=Category.choices)
    # Who to call, and how (feedback 13/11/2026: the complete supplier record).
    contact_name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    whatsapp = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    city = models.CharField(max_length=80, blank=True)
    address = models.CharField(max_length=255, blank=True)
    # Legal identifiers on invoices (Cameroon: NIU and RCCM).
    tax_id = models.CharField("NIU", max_length=40, blank=True)
    trade_register = models.CharField("RCCM", max_length=60, blank=True)
    # How they are paid.
    payment_terms = models.CharField(max_length=160, blank=True)
    mobile_money = models.CharField(max_length=32, blank=True)
    bank_details = models.CharField(max_length=160, blank=True)
    # What they do for the agency (feedback 13/11/2026: replaces the 1-5 rating).
    services = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    # Deleted after working on weddings (feedback 13/11/2026): out of the address book, still
    # shown on those weddings. A contact that never worked is deleted for good.
    is_deleted = models.BooleanField(default=False)

    class Meta(TenantModel.Meta):
        ordering = ["name"]
        indexes = [
            models.Index(fields=["organization", "category"]),
            models.Index(fields=["organization", "kind"]),
        ]

    def __str__(self) -> str:
        return self.name


class VendorAssignment(TenantModel):
    """A vendor booked for a wedding: what for, the cost, what has been paid to them."""

    wedding = models.ForeignKey(
        "events.Wedding", on_delete=models.CASCADE, related_name="vendor_assignments"
    )
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="assignments")
    service = models.CharField(max_length=160, blank=True)
    cost = models.BigIntegerField(default=0)
    paid_amount = models.BigIntegerField(default=0)

    class Meta(TenantModel.Meta):
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["organization", "wedding"]),
            models.Index(fields=["organization", "vendor"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cost__gte=0, paid_amount__gte=0)
                & models.Q(paid_amount__lte=models.F("cost")),
                name="vendor_assignment_amounts_valid",
            )
        ]

    def __str__(self) -> str:
        return f"{self.vendor_id} → {self.wedding_id}"

    @property
    def due(self) -> int:
        return self.cost - self.paid_amount
