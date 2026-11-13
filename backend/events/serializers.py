from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.utils import timezone
from rest_framework import serializers

from accounts.models import Membership, User
from core.tenant import require_current_organization

from . import selectors
from .calendar import MAX_DAYS
from .models import Task, Wedding


class MemberField(serializers.UUIDField):
    """A user id that must be an active member of the current space (tasks' assignee)."""

    def to_internal_value(self, data: Any) -> User:  # type: ignore[override]
        user_id = super().to_internal_value(data)
        membership = (
            Membership.objects.select_related("user")
            .filter(organization=require_current_organization(), user_id=user_id, is_active=True)
            .first()
        )
        if membership is None:
            raise serializers.ValidationError("Choisissez un membre de l’équipe.")
        return membership.user

    def to_representation(self, value: Any) -> str | None:  # type: ignore[override]
        return str(value.pk) if isinstance(value, User) else (str(value) if value else None)


class TaskSerializer(serializers.ModelSerializer[Task]):
    assignee = MemberField(required=False, allow_null=True)
    assignee_name = serializers.CharField(source="assignee.full_name", read_only=True, default=None)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "wedding",
            "title",
            "assignee",
            "assignee_name",
            "due_date",
            "status",
            "status_label",
            "notes",
            "done_at",
        ]
        read_only_fields = ["id", "wedding", "status", "done_at"]


class WeddingSerializer(serializers.ModelSerializer[Wedding]):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    tasks_total = serializers.IntegerField(read_only=True, default=0)
    tasks_done = serializers.IntegerField(read_only=True, default=0)
    vendors_count = serializers.IntegerField(read_only=True, default=0)
    progress = serializers.SerializerMethodField()
    days_left = serializers.SerializerMethodField()
    contract_number = serializers.CharField(source="contract.number", read_only=True, default=None)
    # Creation only: add the agency's standard task list (complement §11).
    standard_tasks = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = Wedding
        fields = [
            "id",
            "title",
            "date",
            "venue",
            "guest_count",
            "budget",
            "status",
            "status_label",
            "contract",
            "contract_number",
            "client",
            "tasks_total",
            "tasks_done",
            "progress",
            "vendors_count",
            "days_left",
            "standard_tasks",
        ]
        read_only_fields = ["id", "contract", "client"]

    def get_progress(self, wedding: Wedding) -> int:
        return selectors.progress(
            getattr(wedding, "tasks_done", 0), getattr(wedding, "tasks_total", 0)
        )

    def get_days_left(self, wedding: Wedding) -> int | None:
        return (wedding.date - timezone.localdate()).days if wedding.date else None

    def validate_title(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Indiquez le couple.")
        return value.strip()


class CalendarQuerySerializer(serializers.Serializer[Any]):
    """``?from=&to=&member=&kinds=&statuses=`` (« from » is a Python keyword: fields are
    declared here). ``kinds`` and ``statuses`` are comma-separated lists."""

    def get_fields(self) -> dict[str, serializers.Field[Any, Any, Any, Any]]:
        return {
            "from": serializers.DateField(),
            "to": serializers.DateField(),
            "member": serializers.UUIDField(required=False),
            "kinds": serializers.CharField(required=False, allow_blank=True),
            "statuses": serializers.CharField(required=False, allow_blank=True),
        }

    @staticmethod
    def _split(value: str, allowed: Iterable[str], field: str) -> list[str]:
        values = [v.strip() for v in value.split(",") if v.strip()]
        unknown = sorted(set(values) - set(allowed))
        if unknown:
            raise serializers.ValidationError({field: [f"Inconnu : {', '.join(unknown)}."]})
        return values

    def validate_kinds(self, value: str) -> list[str]:
        from .calendar import KINDS

        return self._split(value, KINDS, "kinds")

    def validate_statuses(self, value: str) -> list[str]:
        from reservations.models import Reservation

        return self._split(value, Reservation.Status.values, "statuses")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["to"] < attrs["from"]:
            raise serializers.ValidationError({"to": ["La fin précède le début."]})
        if (attrs["to"] - attrs["from"]).days > MAX_DAYS:
            raise serializers.ValidationError({"to": ["Deux mois au maximum."]})
        return attrs
