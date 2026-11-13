"""Internal alerts (reservations-stock.md §2, §5.4, §8): notices for the team, never messages
sent to clients. One row per situation (``dedupe_key``); it resolves itself when the situation
is over, or a member marks it as handled."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from core.models import TenantModel


class Alert(TenantModel):
    class Kind(models.TextChoices):
        OVERDUE_PAYMENT = "overdue_payment", "Échéance en retard"
        OVERDUE_INVOICE = "overdue_invoice", "Facture en retard"
        LATE_TASKS = "late_tasks", "Tâches en retard"
        WEDDING_UNREADY = "wedding_unready", "Mariage proche, tâches à finir"
        BELOW_THRESHOLD = "below_threshold", "Article sous son seuil"
        MAINTENANCE_LATE = "maintenance_late", "Maintenance qui dure"
        DAMAGED_UNIT = "damaged_unit", "Matériel abîmé non traité"
        STOCK_SHORTAGE = "stock_shortage", "Stock insuffisant pour une réservation"
        LATE_RETURN = "late_return", "Retour en retard"

    class Severity(models.TextChoices):
        CRITICAL = "critical", "Urgent"
        SERIOUS = "serious", "Important"
        WARNING = "warning", "À surveiller"

    kind = models.CharField(max_length=32, choices=Kind.choices)
    severity = models.CharField(max_length=16, choices=Severity.choices)
    title = models.CharField(max_length=160)
    subtitle = models.CharField(max_length=160, blank=True)
    # Figures of the situation (amount, days, count…) and its targets (contract, wedding).
    data = models.JSONField(default=dict, blank=True)
    occurred_on = models.DateField(null=True, blank=True)
    dedupe_key = models.CharField(max_length=120)
    resolved_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    dismissed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta(TenantModel.Meta):
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "resolved_at", "dismissed_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "dedupe_key"], name="unique_alert_dedupe_key"
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} — {self.title}"

    @property
    def is_open(self) -> bool:
        return self.resolved_at is None and self.dismissed_at is None
