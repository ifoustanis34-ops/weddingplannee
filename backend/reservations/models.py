"""Reservations (docs/specs/reservations-stock.md §4.1): everything a client orders for a date —
equipment rental or sale, services, or a mix. Amounts are integer FCFA."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q

from core.models import TenantModel


class Reservation(TenantModel):
    class Kind(models.TextChoices):
        RENTAL = "rental", "Location"
        SALE = "sale", "Vente"
        SERVICE = "service", "Prestation"
        MIXED = "mixed", "Mixte"

    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        QUOTE_SENT = "quote_sent", "Devis envoyé"
        AWAITING_DEPOSIT = "awaiting_deposit", "En attente d’acompte"
        CONFIRMED = "confirmed", "Confirmée"
        PREPARING = "preparing", "En préparation"
        DELIVERED = "delivered", "Livrée"
        INSTALLED = "installed", "Installée"
        IN_PROGRESS = "in_progress", "En cours"
        PICKED_UP = "picked_up", "Récupérée"
        CLOSED = "closed", "Clôturée"
        CANCELLED = "cancelled", "Annulée"

    class SecurityStatus(models.TextChoices):
        NONE = "none", "Pas de caution"
        HELD = "held", "Caution encaissée"
        REFUNDED = "refunded", "Caution restituée"
        RETAINED = "retained", "Caution retenue"

    number = models.CharField(max_length=32)
    client = models.ForeignKey("crm.Client", on_delete=models.PROTECT, related_name="reservations")
    wedding = models.ForeignKey(
        "events.Wedding",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservations",
    )
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.RENTAL)
    title = models.CharField(max_length=160)
    venue = models.CharField(max_length=160, blank=True)
    address = models.TextField(blank=True)
    guest_count = models.PositiveIntegerField(null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    # Logistics (§4.1). Equipment is blocked from leaving the warehouse until it is back,
    # plus each item's cleaning delay.
    delivery_at = models.DateTimeField(null=True, blank=True)
    setup_at = models.DateTimeField(null=True, blank=True)
    event_start = models.DateTimeField()
    event_end = models.DateTimeField()
    teardown_at = models.DateTimeField(null=True, blank=True)
    pickup_at = models.DateTimeField(null=True, blank=True)
    return_at = models.DateTimeField(null=True, blank=True)
    # Vehicle used for the delivery and pickup (§4.3), free text until a fleet exists.
    vehicle = models.CharField(max_length=80, blank=True)
    # Amounts (recomputed by the services; the server is the reference).
    discount = models.BigIntegerField(default=0)
    transport_fee = models.BigIntegerField(default=0)
    setup_fee = models.BigIntegerField(default=0)
    subtotal = models.BigIntegerField(default=0)
    total = models.BigIntegerField(default=0)
    deposit_required = models.BigIntegerField(default=0)
    security_deposit = models.BigIntegerField(default=0)  # caution, sum of the lines
    security_status = models.CharField(
        max_length=16, choices=SecurityStatus.choices, default=SecurityStatus.NONE
    )
    security_retained = models.BigIntegerField(default=0)
    notes = models.TextField(blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.TextField(blank=True)
    refund_due = models.BigIntegerField(default=0)  # after a cancellation (policy in settings)

    class Meta(TenantModel.Meta):
        ordering = ["-event_start"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "event_start"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "number"], name="unique_reservation_number"
            ),
            models.CheckConstraint(
                condition=Q(
                    discount__gte=0,
                    transport_fee__gte=0,
                    setup_fee__gte=0,
                    total__gte=0,
                    deposit_required__gte=0,
                    security_deposit__gte=0,
                    security_retained__gte=0,
                ),
                name="reservation_amounts_positive",
            ),
            models.CheckConstraint(
                condition=Q(event_end__gte=models.F("event_start")),
                name="reservation_event_ordered",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.number} — {self.title}"


class ReservationLine(TenantModel):
    class Kind(models.TextChoices):
        RENTAL = "rental", "Location"
        SALE = "sale", "Vente"
        PACK = "pack", "Pack"
        SERVICE = "service", "Prestation"
        FREE = "free", "Ligne libre"
        DAMAGE = "damage", "Casse et pertes"

    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name="lines")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    item = models.ForeignKey(
        "stock.Item", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    pack = models.ForeignKey(
        "stock.Pack", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    service = models.ForeignKey(
        "catalog.ServiceItem", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    label = models.CharField(max_length=160)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.BigIntegerField(default=0)
    period_days = models.PositiveSmallIntegerField(default=1)  # items rented « par jour »
    deposit = models.BigIntegerField(default=0)  # caution per unit
    amount = models.BigIntegerField(default=0)
    position = models.PositiveSmallIntegerField(default=0)
    # Logistics of equipment lines (checkout and return, §4.1).
    quantity_out = models.PositiveIntegerField(default=0)
    quantity_returned = models.PositiveIntegerField(default=0)
    quantity_damaged = models.PositiveIntegerField(default=0)
    quantity_missing = models.PositiveIntegerField(default=0)

    class Meta(TenantModel.Meta):
        ordering = ["position", "created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(unit_price__gte=0, amount__gte=0, deposit__gte=0, quantity__gt=0),
                name="reservation_line_amounts",
            ),
            # One source at most: an item, a pack or a service (none for a free line).
            models.CheckConstraint(
                condition=(
                    Q(item__isnull=True, pack__isnull=True)
                    | Q(item__isnull=True, service__isnull=True)
                    | Q(pack__isnull=True, service__isnull=True)
                ),
                name="reservation_line_one_source",
            ),
        ]

    def __str__(self) -> str:
        return self.label


class ReservationPayment(TenantModel):
    """Money received on a reservation: payments, the security deposit and its refund."""

    class Kind(models.TextChoices):
        PAYMENT = "payment", "Paiement"
        SECURITY = "security", "Caution encaissée"
        SECURITY_REFUND = "security_refund", "Caution restituée"

    class Method(models.TextChoices):
        CASH = "cash", "Espèces"
        TRANSFER = "transfer", "Virement"
        ORANGE_MONEY = "orange_money", "Orange Money"
        MTN_MOMO = "mtn_momo", "MTN MoMo"
        WAVE = "wave", "Wave"
        CHEQUE = "cheque", "Chèque"

    reservation = models.ForeignKey(Reservation, on_delete=models.PROTECT, related_name="payments")
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.PAYMENT)
    amount = models.BigIntegerField()
    method = models.CharField(max_length=16, choices=Method.choices)
    paid_at = models.DateField()
    reference = models.CharField(max_length=80, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    is_cancelled = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.TextField(blank=True)

    class Meta(TenantModel.Meta):
        ordering = ["-paid_at", "-created_at"]
        indexes = [models.Index(fields=["organization", "paid_at"])]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="reservation_payment_positive")
        ]


class ReservationLog(TenantModel):
    """History of the reservation sheet (§4.2): who did what, when."""

    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name="logs")
    action = models.CharField(max_length=40)
    message = models.CharField(max_length=255)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )

    class Meta(TenantModel.Meta):
        ordering = ["-created_at"]
