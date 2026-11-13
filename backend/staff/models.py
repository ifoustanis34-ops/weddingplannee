"""Staff (docs/specs/reservations-stock.md §7): people, assignments, tasks, attendance, pay.

A staff member is not necessarily a user: day workers and freelancers usually have no login.
When they do (team lead, staff), `user` links the record to « Mes missions » and self check-in.
"""

from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.db import models
from django.db.models import Q

from core.models import TenantModel


def private_path(instance: Any, filename: str) -> str:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"org/{instance.organization_id}/staff/{uuid.uuid4().hex}.{extension}"


class StaffMember(TenantModel):
    class Kind(models.TextChoices):
        EMPLOYEE = "employee", "Salarié"
        DAY_WORKER = "day_worker", "Journalier"
        FREELANCE = "freelance", "Freelance"

    class PayMode(models.TextChoices):
        MONTHLY = "monthly", "Mensuel"
        DAILY = "daily", "Journalier"
        MISSION = "mission", "À la mission"
        HOURLY = "hourly", "Horaire"

    full_name = models.CharField(max_length=120)
    photo = models.FileField(upload_to=private_path, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    position = models.CharField(max_length=80)  # chef d’équipe, magasinier, livreur…
    department = models.CharField(max_length=80, blank=True)  # logistique, décoration…
    # Matricule printed on the badge (« ME-2026-001 »), given automatically.
    employee_number = models.CharField(max_length=32, blank=True)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.DAY_WORKER)
    skills = models.JSONField(default=list, blank=True)
    pay_mode = models.CharField(max_length=16, choices=PayMode.choices, default=PayMode.DAILY)
    pay_rate = models.BigIntegerField(default=0)
    mobile_money = models.CharField(max_length=32, blank=True)
    emergency_contact = models.CharField(max_length=160, blank=True)
    notes = models.TextField(blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    is_active = models.BooleanField(default=True)
    # Deleted (feedback 13/11/2026): out of every list; missions, pay and payments stay.
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantModel.Meta):
        ordering = ["full_name"]
        constraints = [
            models.CheckConstraint(condition=Q(pay_rate__gte=0), name="staff_pay_rate_positive"),
            models.UniqueConstraint(
                fields=["organization", "user"],
                condition=Q(user__isnull=False),
                name="unique_staff_user",
            ),
        ]

    def __str__(self) -> str:
        return self.full_name


class Assignment(TenantModel):
    """A person on a reservation, for one logistic step or the whole event (§7)."""

    class Step(models.TextChoices):
        ALL = "all", "Toute la réservation"
        DELIVERY = "delivery", "Livraison"
        SETUP = "setup", "Installation"
        EVENT = "event", "Événement"
        TEARDOWN = "teardown", "Démontage"
        PICKUP = "pickup", "Récupération"
        RETURN = "return", "Retour"

    staff = models.ForeignKey(StaffMember, on_delete=models.PROTECT, related_name="assignments")
    reservation = models.ForeignKey(
        "reservations.Reservation", on_delete=models.CASCADE, related_name="assignments"
    )
    step = models.CharField(max_length=16, choices=Step.choices, default=Step.ALL)
    role = models.CharField(max_length=80, blank=True)
    start = models.DateTimeField()
    end = models.DateTimeField()

    class Meta(TenantModel.Meta):
        ordering = ["start"]
        indexes = [models.Index(fields=["organization", "start"])]
        constraints = [
            models.CheckConstraint(condition=Q(end__gt=models.F("start")), name="assignment_order")
        ]


class StaffTask(TenantModel):
    class Status(models.TextChoices):
        TODO = "todo", "À faire"
        DONE = "done", "Faite, à valider"
        VALIDATED = "validated", "Validée"

    staff = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name="tasks")
    reservation = models.ForeignKey(
        "reservations.Reservation", on_delete=models.CASCADE, related_name="staff_tasks"
    )
    title = models.CharField(max_length=160)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.TODO)
    comment = models.TextField(blank=True)
    photo = models.FileField(upload_to=private_path, blank=True)  # end of setup (§7)
    # Done by the person (or for them), then checked by the owner or the planner.
    done_at = models.DateTimeField(null=True, blank=True)
    done_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    rejection_reason = models.CharField(max_length=255, blank=True)

    class Meta(TenantModel.Meta):
        ordering = ["status", "created_at"]


class Attendance(TenantModel):
    """Check-in and check-out of a mission (§7). One per assignment."""

    class Status(models.TextChoices):
        PRESENT = "present", "Présent"
        LATE = "late", "En retard"
        ABSENT = "absent", "Absent"

    staff = models.ForeignKey(StaffMember, on_delete=models.PROTECT, related_name="attendances")
    assignment = models.OneToOneField(
        Assignment, on_delete=models.CASCADE, null=True, blank=True, related_name="attendance"
    )
    date = models.DateField()
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PRESENT)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    note = models.CharField(max_length=255, blank=True)

    class Meta(TenantModel.Meta):
        ordering = ["-date", "check_in"]
        indexes = [models.Index(fields=["organization", "date"])]


class PayPeriod(TenantModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "En cours"
        VALIDATED = "validated", "Validée"
        PAID = "paid", "Payée"

    start = models.DateField()
    end = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    validated_at = models.DateTimeField(null=True, blank=True)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )

    class Meta(TenantModel.Meta):
        ordering = ["-start"]
        constraints = [
            models.CheckConstraint(condition=Q(end__gte=models.F("start")), name="pay_period_order")
        ]


class PayLine(TenantModel):
    """What one person earns over a period: base (attendance and missions) + bonuses − advances."""

    period = models.ForeignKey(PayPeriod, on_delete=models.CASCADE, related_name="lines")
    staff = models.ForeignKey(StaffMember, on_delete=models.PROTECT, related_name="pay_lines")
    days = models.PositiveIntegerField(default=0)
    missions = models.PositiveIntegerField(default=0)
    hours = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    base = models.BigIntegerField(default=0)
    bonuses = models.BigIntegerField(default=0)
    advances = models.BigIntegerField(default=0)
    # Paid the same day during the period (« Payer la journée »): deducted, never paid twice.
    already_paid = models.BigIntegerField(default=0)
    total = models.BigIntegerField(default=0)
    paid_at = models.DateField(null=True, blank=True)
    method = models.CharField(max_length=16, blank=True)
    expense = models.ForeignKey(
        "finance.Expense", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta(TenantModel.Meta):
        ordering = ["staff__full_name"]
        constraints = [
            models.UniqueConstraint(fields=["period", "staff"], name="unique_pay_line"),
            models.CheckConstraint(
                condition=Q(bonuses__gte=0, advances__gte=0, base__gte=0),
                name="pay_line_amounts_positive",
            ),
        ]


class StaffPayment(TenantModel):
    """A payment made on the spot (feedback 13/11/2026): the day workers of an event are paid the
    same day; the pay period then deducts it. Creates its expense « Salaires et journaliers »."""

    staff = models.ForeignKey(StaffMember, on_delete=models.PROTECT, related_name="payments")
    reservation = models.ForeignKey(
        "reservations.Reservation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_payments",
    )
    date = models.DateField()
    amount = models.BigIntegerField()
    method = models.CharField(max_length=16)
    note = models.CharField(max_length=160, blank=True)
    expense = models.ForeignKey(
        "finance.Expense", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta(TenantModel.Meta):
        ordering = ["-date", "staff__full_name"]
        indexes = [models.Index(fields=["organization", "date"])]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="staff_payment_positive"),
        ]
