"""Guests and their tickets (docs/specs/devis-billets.md §6, §7, §10).

The complement's « Guest / CheckIn » (CLAUDE.md §8) become Guest (the invited person or
family) + Ticket (their signed ticket); CheckIn comes with the scan (R6).
"""

from __future__ import annotations

from typing import Any

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import TenantModel


def default_categories() -> list[str]:
    return ["Standard", "Famille", "VIP"]


class TicketDesign(TenantModel):
    """What every ticket of a wedding shows (§2f « Mariage (billets) »), one per wedding."""

    wedding = models.OneToOneField(
        "events.Wedding", on_delete=models.CASCADE, related_name="ticket_design"
    )
    palette = models.CharField(max_length=24, default="noir-or")
    partner_1 = models.CharField(max_length=40, blank=True)
    partner_2 = models.CharField(max_length=40, blank=True)
    title = models.CharField(max_length=40, default="Invitation officielle")
    subtitle = models.CharField(max_length=40, default="À notre mariage")
    intro = models.CharField(
        max_length=200,
        default=(
            "Avec l’amour comme guide et la volonté de bâtir un avenir ensemble, "
            "nous avons la joie de vous inviter à célébrer notre union."
        ),
    )
    panel_text = models.CharField(max_length=60, default="Deux cœurs, une même histoire")
    bottom_slogan = models.CharField(max_length=60, default="Amour • Engagement • Éternité")
    script_line = models.CharField(
        max_length=70, default="Votre présence est un bonheur pour nous !"
    )
    starts_at = models.DateTimeField(null=True, blank=True)
    venue = models.CharField(max_length=80, blank=True)
    address = models.CharField(max_length=80, blank=True)
    dress_code = models.CharField(max_length=60, default="Tenue élégante")
    stub_title = models.CharField(max_length=30, default="Billet d’invitation")
    stub_subtitle = models.CharField(max_length=30, default="Événement mariage")
    stub_script = models.CharField(max_length=50, default="Merci de confirmer votre présence")
    stub_footer = models.CharField(max_length=30, default="Ensemble pour toujours")
    show_monogram = models.BooleanField(default=False)
    categories: models.JSONField[list[str]] = models.JSONField(
        default=default_categories, blank=True
    )


class Guest(TenantModel):
    """One invitation: a person or a family with a number of seats."""

    class Rsvp(models.TextChoices):
        PENDING = "pending", "En attente"
        ACCEPTED = "accepted", "Confirmé"
        DECLINED = "declined", "Décliné"

    wedding = models.ForeignKey("events.Wedding", on_delete=models.CASCADE, related_name="guests")
    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    seats = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(50)]
    )
    category = models.CharField(max_length=30, blank=True)
    table = models.CharField(max_length=30, blank=True)
    rsvp_status = models.CharField(max_length=10, choices=Rsvp.choices, default=Rsvp.PENDING)
    rsvp_at = models.DateTimeField(null=True, blank=True)
    notes = models.CharField(max_length=200, blank=True)

    class Meta(TenantModel.Meta):
        ordering = ["name"]
        indexes = [models.Index(fields=["organization", "wedding"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(seats__gte=1) & models.Q(seats__lte=50),
                name="guest_seats_range",
            )
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def ticket(self) -> Ticket | None:
        """The guest's current ticket (prefetched as `active_tickets` by the list)."""
        cached: Any = getattr(self, "active_tickets", None)
        if cached is not None:
            return cached[0] if cached else None
        return self.tickets.filter(status=Ticket.Status.ACTIVE).first()


class Ticket(TenantModel):
    """A signed ticket. Reissuing cancels it and creates a new one with a new token (§7)."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Actif"
        CANCELLED = "cancelled", "Annulé"
        REISSUED = "reissued", "Réémis"

    wedding = models.ForeignKey("events.Wedding", on_delete=models.CASCADE, related_name="tickets")
    guest = models.ForeignKey(Guest, on_delete=models.CASCADE, related_name="tickets")
    # The random part of the token (hex): finds the ticket and re-renders its QR. The token
    # itself is never stored, only its SHA-256 (offline scan lists, §8).
    token_id = models.CharField(max_length=32, unique=True)
    token_hash = models.CharField(max_length=64, unique=True)
    number = models.PositiveIntegerField()
    code = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    issued_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    document = models.ForeignKey(
        "documents.GeneratedDocument",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta(TenantModel.Meta):
        ordering = ["number"]
        indexes = [models.Index(fields=["organization", "wedding", "status"])]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "wedding", "number"], name="unique_ticket_number"
            ),
            models.UniqueConstraint(
                fields=["guest"],
                condition=models.Q(status="active"),
                name="one_active_ticket_per_guest",
            ),
        ]

    def __str__(self) -> str:
        return self.code
