"""Weddings and their preparation tasks (CLAUDE.md §7.6, complement §11)."""

from __future__ import annotations

from django.conf import settings
from django.db import models

from core.models import TenantModel


class Wedding(TenantModel):
    class Status(models.TextChoices):
        PLANNED = "planned", "En préparation"
        DONE = "done", "Célébré"
        CANCELLED = "cancelled", "Annulé"

    title = models.CharField(max_length=160)
    date = models.DateField(null=True, blank=True)
    venue = models.CharField(max_length=160, blank=True)
    guest_count = models.PositiveIntegerField(null=True, blank=True)
    budget = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PLANNED)
    contract = models.OneToOneField(
        "contracts.Contract",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wedding",
    )
    client = models.ForeignKey(
        "crm.Client", on_delete=models.SET_NULL, null=True, blank=True, related_name="weddings"
    )

    class Meta(TenantModel.Meta):
        ordering = ["date"]
        indexes = [models.Index(fields=["organization", "date"])]

    def __str__(self) -> str:
        return self.title


class Task(TenantModel):
    """Preparation task of a wedding (CLAUDE.md §7.6). Done ÷ total = the wedding's progress."""

    class Status(models.TextChoices):
        TODO = "todo", "À faire"
        DONE = "done", "Faite"

    wedding = models.ForeignKey(Wedding, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.TODO)
    notes = models.TextField(blank=True)
    done_at = models.DateTimeField(null=True, blank=True)
    # The J-2 email to the assignee is sent once per due date (CLAUDE.md §7.6).
    alert_sent_for = models.DateField(null=True, blank=True, editable=False)

    class Meta(TenantModel.Meta):
        ordering = ["status", "due_date", "created_at"]
        indexes = [
            models.Index(fields=["organization", "wedding"]),
            models.Index(fields=["organization", "status", "due_date"]),
        ]

    def __str__(self) -> str:
        return self.title


class TaskTemplateItem(TenantModel):
    """One line of the agency's standard task list (complement §11): due N days before."""

    title = models.CharField(max_length=200)
    days_before = models.PositiveSmallIntegerField()
    position = models.PositiveSmallIntegerField(default=0)

    class Meta(TenantModel.Meta):
        ordering = ["position", "-days_before"]

    def __str__(self) -> str:
        return f"{self.title} (J-{self.days_before})"
