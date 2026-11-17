"""Staff API (docs/specs/reservations-stock.md §7, §12).

- People, assignments, tasks: read by owner, planner, assistant, accountant; written by owner
  and planner. Pay rates and pay: owner and accountant only (never sent to the others);
  validating a pay period: the owner.
- Check-in: owner and planner for anyone; the team lead for the people on a reservation he is
  assigned to; a staff member for himself only (`open_to_field_roles`).
- « Mes missions »: the signed-in user's own assignments, equipment without prices.
"""

from __future__ import annotations

import urllib.parse
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import QuerySet
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, serializers, status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Membership
from accounts.views import PublicAPIView
from core.exceptions import BusinessError
from core.fields import TenantPrimaryKeyRelatedField
from core.permissions import IsTenantMember
from core.signed_files import signed_url
from core.tenant import require_current_organization
from documents import images, rendering
from documents import services as branding_services
from documents.quote_document import long_date, money
from organizations.timezones import org_tz
from reservations.models import Reservation

from . import services
from .models import (
    Assignment,
    Attendance,
    PayLine,
    PayPeriod,
    StaffMember,
    StaffPayment,
    StaffTask,
)

Role = Membership.Role
READ = frozenset({Role.OWNER, Role.PLANNER, Role.ASSISTANT, Role.ACCOUNTANT})
WRITE = frozenset({Role.OWNER, Role.PLANNER})
PAY = frozenset({Role.OWNER, Role.ACCOUNTANT})
MONEY_FIELDS = ("pay_rate",)


def role_of(request: Request) -> str | None:
    membership = getattr(request, "membership", None)
    return membership.role if membership is not None else None


def me(request: Request) -> StaffMember | None:
    return StaffMember.objects.filter(user=request.user, is_active=True).first()


class StaffPermission(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        role = role_of(request)
        if getattr(view, "pay_view", False):
            self.message = "La paie est réservée au propriétaire et au comptable."
            return role in PAY
        if request.method in SAFE_METHODS:
            self.message = "Votre rôle n’a pas accès au personnel."
            return role in READ
        self.message = "Seuls le propriétaire et le planner gèrent l’équipe."
        return role in WRITE


PERMISSIONS = [IsTenantMember, StaffPermission]


def _today() -> date:
    return services.today()


def _tz() -> Any:
    return org_tz(require_current_organization())


# --- Serializers ---------------------------------------------------------------------------------


class StaffSerializer(serializers.ModelSerializer[StaffMember]):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    pay_mode_label = serializers.CharField(source="get_pay_mode_display", read_only=True)
    photo_url = serializers.SerializerMethodField()
    has_account = serializers.SerializerMethodField()
    today = serializers.SerializerMethodField()
    skills = serializers.ListField(child=serializers.CharField(max_length=60), required=False)
    pay_rate = serializers.IntegerField(min_value=0, required=False)

    class Meta:
        model = StaffMember
        fields = [
            "id",
            "full_name",
            "photo_url",
            "phone",
            "position",
            "department",
            "employee_number",
            "kind",
            "kind_label",
            "skills",
            "pay_mode",
            "pay_mode_label",
            "pay_rate",
            "mobile_money",
            "emergency_contact",
            "notes",
            "user",
            "has_account",
            "is_active",
            "today",
        ]
        read_only_fields = ["id", "user", "employee_number"]

    def validate_full_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Indiquez le nom.")
        return value

    def get_photo_url(self, staff: StaffMember) -> str | None:
        return signed_url(staff.photo.name) if staff.photo else None

    def get_has_account(self, staff: StaffMember) -> bool:
        return staff.user_id is not None

    def get_today(self, staff: StaffMember) -> dict[str, Any]:
        """Availability of the day (§7 list): free, on a mission (where), absent."""
        busy: dict[str, list[Assignment]] = self.context.get("busy_today", {})
        absent: set[str] = self.context.get("absent_today", set())
        if str(staff.pk) in absent:
            return {"status": "absent", "missions": []}
        missions = busy.get(str(staff.pk), [])
        return {
            "status": "busy" if missions else "free",
            "missions": [
                {
                    "reservation": str(a.reservation_id),
                    "number": a.reservation.number,
                    "step": a.step,
                    "start": a.start,
                }
                for a in missions
            ],
        }

    def to_representation(self, instance: StaffMember) -> dict[str, Any]:
        data = dict(super().to_representation(instance))
        if self.context.get("role") not in PAY:
            for field in MONEY_FIELDS:
                data[field] = None
        return data


class AssignmentSerializer(serializers.ModelSerializer[Assignment]):
    staff_name = serializers.CharField(source="staff.full_name", read_only=True)
    staff_position = serializers.CharField(source="staff.position", read_only=True)
    step_label = serializers.CharField(source="get_step_display", read_only=True)
    reservation_number = serializers.CharField(source="reservation.number", read_only=True)
    reservation_title = serializers.CharField(source="reservation.title", read_only=True)
    attendance = serializers.SerializerMethodField()
    conflicts = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = [
            "id",
            "staff",
            "staff_name",
            "staff_position",
            "reservation",
            "reservation_number",
            "reservation_title",
            "step",
            "step_label",
            "role",
            "start",
            "end",
            "attendance",
            "conflicts",
        ]
        read_only_fields = fields

    def get_attendance(self, assignment: Assignment) -> dict[str, Any] | None:
        attendance = getattr(assignment, "attendance", None)
        if attendance is None:
            return None
        return {
            "status": attendance.status,
            "check_in": attendance.check_in,
            "check_out": attendance.check_out,
            "hours": float(attendance.hours),
            "note": attendance.note,
        }

    def get_conflicts(self, assignment: Assignment) -> list[str]:
        if not self.context.get("with_conflicts"):
            return []
        return [
            c.message
            for c in services.conflicts(
                assignment.staff, assignment.start, assignment.end, exclude=assignment.pk
            )
        ]


class AssignInput(serializers.Serializer[Any]):
    reservation = TenantPrimaryKeyRelatedField(Reservation)
    staff = TenantPrimaryKeyRelatedField(StaffMember)
    step = serializers.ChoiceField(choices=Assignment.Step.choices, default=Assignment.Step.ALL)
    role = serializers.CharField(max_length=80, required=False, allow_blank=True, default="")


class TaskSerializer(serializers.ModelSerializer[StaffTask]):
    staff = TenantPrimaryKeyRelatedField(StaffMember)
    reservation = TenantPrimaryKeyRelatedField(Reservation)
    staff_name = serializers.CharField(source="staff.full_name", read_only=True)
    reservation_number = serializers.CharField(source="reservation.number", read_only=True)
    reservation_title = serializers.CharField(source="reservation.title", read_only=True)
    event_start = serializers.DateTimeField(source="reservation.event_start", read_only=True)
    staff_position = serializers.CharField(source="staff.position", read_only=True)
    staff_has_account = serializers.SerializerMethodField()
    venue = serializers.CharField(source="reservation.venue", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    done_by_name = serializers.CharField(source="done_by.full_name", read_only=True, default=None)
    validated_by_name = serializers.CharField(
        source="validated_by.full_name", read_only=True, default=None
    )
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = StaffTask
        fields = [
            "id",
            "staff",
            "staff_name",
            "staff_position",
            "reservation",
            "reservation_number",
            "reservation_title",
            "event_start",
            "venue",
            "staff_has_account",
            "title",
            "status",
            "status_label",
            "comment",
            "photo_url",
            "done_at",
            "done_by_name",
            "validated_at",
            "validated_by_name",
            "rejection_reason",
        ]
        read_only_fields = [
            "id",
            "status",
            "done_at",
            "validated_at",
            "rejection_reason",
        ]

    def get_staff_has_account(self, task: StaffTask) -> bool:
        return task.staff.user_id is not None

    def get_photo_url(self, task: StaffTask) -> str | None:
        return signed_url(task.photo.name) if task.photo else None

    def validate_title(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Décrivez la tâche.")
        return value


class PayLineSerializer(serializers.ModelSerializer[PayLine]):
    staff_name = serializers.CharField(source="staff.full_name", read_only=True)
    position = serializers.CharField(source="staff.position", read_only=True)
    pay_mode = serializers.CharField(source="staff.pay_mode", read_only=True)
    pay_rate = serializers.IntegerField(source="staff.pay_rate", read_only=True)
    hours = serializers.FloatField(read_only=True)

    class Meta:
        model = PayLine
        fields = [
            "id",
            "staff",
            "staff_name",
            "position",
            "pay_mode",
            "pay_rate",
            "days",
            "missions",
            "hours",
            "base",
            "bonuses",
            "advances",
            "already_paid",
            "total",
            "paid_at",
            "method",
        ]
        read_only_fields = fields


class PayPeriodSerializer(serializers.ModelSerializer[PayPeriod]):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    lines = PayLineSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = PayPeriod
        fields = ["id", "start", "end", "status", "status_label", "validated_at", "lines", "total"]
        read_only_fields = fields

    def get_total(self, period: PayPeriod) -> int:
        return sum(line.total for line in period.lines.all())


# --- People --------------------------------------------------------------------------------------


def _day_context(request: Request) -> dict[str, Any]:
    tz = _tz()
    day = _today()
    first = datetime.combine(day, time.min, tzinfo=tz)
    busy: dict[str, list[Assignment]] = {}
    for assignment in (
        Assignment.objects.filter(start__lt=first + timedelta(days=1), end__gt=first)
        .exclude(reservation__status="cancelled")
        .select_related("reservation")
    ):
        busy.setdefault(str(assignment.staff_id), []).append(assignment)
    absent = {
        str(staff_id)
        for staff_id in Attendance.objects.filter(
            date=day, status=Attendance.Status.ABSENT
        ).values_list("staff_id", flat=True)
    }
    return {"busy_today": busy, "absent_today": absent, "role": role_of(request)}


class StaffListView(generics.ListCreateAPIView[StaffMember]):
    """`?search=&active=false` — the list shows today's availability (§7)."""

    permission_classes = PERMISSIONS
    serializer_class = StaffSerializer
    pagination_class = None

    def get_queryset(self) -> QuerySet[StaffMember]:
        if getattr(self, "swagger_fake_view", False):
            return StaffMember.all_tenants.none()
        people = StaffMember.objects.filter(is_deleted=False)
        params = self.request.query_params
        people = people.filter(is_active=params.get("active") != "false")
        if params.get("search"):
            people = people.filter(full_name__icontains=params["search"].strip())
        return people

    def get_serializer_context(self) -> dict[str, Any]:
        return {**super().get_serializer_context(), **_day_context(self.request)}

    def perform_create(self, serializer: StaffSerializer) -> None:  # type: ignore[override]
        if role_of(self.request) not in PAY:
            serializer.validated_data.pop("pay_rate", None)  # the planner sets no salary
        member = serializer.save(created_by=self.request.user)
        services.ensure_employee_number(member)  # « ME-2026-011 » from the start


class StaffDetailView(generics.RetrieveUpdateDestroyAPIView[StaffMember]):
    """Edit, deactivate (« is_active ») or delete (feedback 13/11/2026: owner and planner,
    audited). Deleting keeps the missions done, check-ins and pay (`services.delete_staff`)."""

    permission_classes = PERMISSIONS
    serializer_class = StaffSerializer
    http_method_names = ["get", "patch", "delete"]

    @extend_schema(responses={200: OpenApiResponse(description="Ce que la suppression a fait")})
    def delete(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        from core import audit

        staff: StaffMember = self.get_object()
        name = staff.full_name
        audit.record("staff.deleted", staff, request=request, changes={"name": name})
        done = services.delete_staff(staff)
        return Response(
            {
                "permanent": done.permanent,
                "removed_assignments": done.removed_assignments,
                "access_closed": done.access_closed,
            }
        )

    def get_queryset(self) -> QuerySet[StaffMember]:
        if getattr(self, "swagger_fake_view", False):
            return StaffMember.all_tenants.none()
        return StaffMember.objects.filter(is_deleted=False)

    def get_serializer_context(self) -> dict[str, Any]:
        return {**super().get_serializer_context(), **_day_context(self.request)}

    def perform_update(self, serializer: StaffSerializer) -> None:  # type: ignore[override]
        if role_of(self.request) not in PAY:
            serializer.validated_data.pop("pay_rate", None)
            serializer.validated_data.pop("pay_mode", None)
        serializer.save()


class StaffPhotoView(APIView):
    permission_classes = PERMISSIONS
    parser_classes = [MultiPartParser]

    @extend_schema(responses={200: OpenApiResponse(description="URL signée de la photo")})
    def post(self, request: Request, pk: str) -> Response:
        from django.core.files.base import ContentFile

        staff: StaffMember = generics.get_object_or_404(
            StaffMember.objects.filter(is_deleted=False), pk=pk
        )
        upload = request.FILES.get("file")
        if upload is None:
            raise BusinessError("invalid", "Choisissez une photo.", {"file": ["Obligatoire."]})
        content = upload.read()
        if images.sniff(content) == "svg":
            raise BusinessError("invalid", "Choisissez une photo (JPEG, PNG ou WebP).")
        processed = images.process_photo(content)
        if staff.photo:
            staff.photo.delete(save=False)
        staff.photo.save(f"photo.{processed.extension}", ContentFile(processed.content), save=True)
        return Response({"photo_url": signed_url(staff.photo.name)})


class StaffAccountSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=[(r.value, r.label) for r in Role if r != Role.OWNER], default=Role.STAFF
    )
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class StaffAccountView(APIView):
    """« Créer son accès » (feedback 13/11/2026): the owner opens a Wedivo account for a person of
    the staff (role « Personnel », « Chef d’équipe », « Magasinier »…), linked to the record so
    « Mes missions » shows their assignments and tasks. Temporary password, changed at first
    sign-in."""

    permission_classes = [IsTenantMember]

    @extend_schema(request=StaffAccountSerializer, responses={201: None})
    def post(self, request: Request, pk: str) -> Response:
        from accounts import services as account_services
        from core import audit

        if role_of(request) != Role.OWNER:
            raise BusinessError(
                "forbidden", "Seul le propriétaire crée les accès.", status_code=403
            )
        serializer = StaffAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        staff: StaffMember = generics.get_object_or_404(
            StaffMember.objects.filter(is_deleted=False), pk=pk
        )
        if staff.user_id is not None:
            raise BusinessError("already_linked", f"{staff.full_name} a déjà un accès.")
        email = serializer.validated_data["email"].strip().lower()
        if StaffMember.objects.filter(user__email__iexact=email).exists():
            raise BusinessError(
                "invalid",
                "Ce compte est déjà relié à une autre personne du personnel.",
                {"email": ["Déjà utilisé."]},
            )
        membership, created = account_services.create_member(
            require_current_organization(),
            account_services.NewMember(
                full_name=staff.full_name,
                email=email,
                phone=staff.phone,
                role=serializer.validated_data["role"],
                password=serializer.validated_data["password"],
            ),
            created_by=request.user,  # type: ignore[arg-type]
        )
        staff.user = membership.user
        staff.save(update_fields=["user", "updated_at"])
        audit.record(
            "membership.created",
            membership,
            request=request,
            changes={"email": email, "role": membership.role, "staff": str(staff.pk)},
        )
        return Response(
            {"email": email, "role": membership.role, "created_account": created},
            status=status.HTTP_201_CREATED,
        )


class StaffStatsView(APIView):
    """Tiles (§7): headcount, missions this week, hours this month, payroll of the month."""

    permission_classes = PERMISSIONS

    def get(self, request: Request) -> Response:
        tz = _tz()
        day = _today()
        monday = day - timedelta(days=day.weekday())
        week = datetime.combine(monday, time.min, tzinfo=tz)
        month_start = day.replace(day=1)
        hours = sum(
            a.hours
            for a in Attendance.objects.filter(
                date__range=(month_start, day), status__in=services.PAYABLE
            )
        )
        payroll: int | None = None
        if role_of(request) in PAY:
            payroll = 0
            for staff in StaffMember.objects.filter(is_active=True):
                line = PayLine(period=PayPeriod(start=month_start, end=day), staff=staff)
                if staff.pay_mode == StaffMember.PayMode.MONTHLY:
                    payroll += staff.pay_rate  # the whole monthly salary is due this month
                else:
                    payroll += services.compute_line(line).base
        return Response(
            {
                "headcount": StaffMember.objects.filter(is_active=True).count(),
                "missions_week": Assignment.objects.filter(
                    start__gte=week, start__lt=week + timedelta(days=7)
                )
                .exclude(reservation__status="cancelled")
                .values("reservation", "staff")
                .distinct()
                .count(),
                "hours_month": float(hours),
                "payroll_month": payroll,
            }
        )


class StaffPlanningView(APIView):
    """Team planning over 7 days (§7): per person, per day, the assignments."""

    permission_classes = PERMISSIONS

    def get(self, request: Request) -> Response:
        tz = _tz()
        try:
            first = date.fromisoformat(request.query_params.get("from", ""))
        except ValueError:
            first = _today() - timedelta(days=_today().weekday())
        start = datetime.combine(first, time.min, tzinfo=tz)
        end = start + timedelta(days=7)
        rows: dict[str, dict[str, Any]] = {
            str(s.pk): {"staff": str(s.pk), "name": s.full_name, "position": s.position, "days": {}}
            for s in StaffMember.objects.filter(is_active=True)
        }
        for a in (
            Assignment.objects.filter(start__lt=end, end__gt=start)
            .exclude(reservation__status="cancelled")
            .select_related("reservation", "attendance")
        ):
            row = rows.get(str(a.staff_id))
            if row is None:
                continue
            local = timezone.localtime(a.start, tz)
            day = max(local.date(), first).isoformat()
            row["days"].setdefault(day, []).append(
                {
                    "assignment": str(a.pk),
                    "reservation": str(a.reservation_id),
                    "number": a.reservation.number,
                    "title": a.reservation.title,
                    "step": a.step,
                    "time": local.strftime("%H:%M"),
                    "attendance": getattr(getattr(a, "attendance", None), "status", None),
                }
            )
        for absence in Attendance.objects.filter(
            date__range=(first, first + timedelta(days=6)), status=Attendance.Status.ABSENT
        ):
            row = rows.get(str(absence.staff_id))
            if row is not None:
                row.setdefault("absent", []).append(absence.date.isoformat())
        return Response(
            {
                "from": first,
                "days": [(first + timedelta(days=i)).isoformat() for i in range(7)],
                "rows": list(rows.values()),
            }
        )


# --- Assignments and tasks -----------------------------------------------------------------------


def _assignments() -> QuerySet[Assignment]:
    return Assignment.objects.select_related("staff", "reservation", "attendance")


class AssignmentListView(APIView):
    """`?reservation=&staff=&from=&to=` · POST `{reservation, staff, step, role}` → conflicts."""

    permission_classes = PERMISSIONS

    @extend_schema(responses=AssignmentSerializer(many=True))
    def get(self, request: Request) -> Response:
        rows = _assignments()
        params = request.query_params
        if params.get("reservation"):
            rows = rows.filter(reservation_id=params["reservation"])
        if params.get("staff"):
            rows = rows.filter(staff__pk=params["staff"])
        context = {"with_conflicts": bool(params.get("reservation"))}
        return Response(AssignmentSerializer(rows[:500], many=True, context=context).data)

    @extend_schema(request=AssignInput, responses=AssignmentSerializer)
    def post(self, request: Request) -> Response:
        data = AssignInput(data=request.data)
        data.is_valid(raise_exception=True)
        assignment, found = services.assign(
            data.validated_data["reservation"],
            data.validated_data["staff"],
            step=data.validated_data["step"],
            role=data.validated_data["role"],
            user=request.user,  # type: ignore[arg-type]
        )
        body = dict(AssignmentSerializer(_assignments().get(pk=assignment.pk)).data)
        body["conflicts"] = [c.message for c in found]
        return Response(body, status=status.HTTP_201_CREATED)


class AssignmentDetailView(APIView):
    permission_classes = PERMISSIONS

    @extend_schema(responses={204: None})
    def delete(self, request: Request, pk: str) -> Response:
        assignment: Assignment = generics.get_object_or_404(Assignment.objects.all(), pk=pk)
        if Attendance.objects.filter(assignment=assignment, check_in__isnull=False).exists():
            raise BusinessError("invalid", "Cette personne a déjà pointé : l’affectation reste.")
        assignment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CheckPermission(BasePermission):
    """Owner and planner for anyone; team lead for his reservations; staff for himself."""

    message = "Vous ne pouvez pas pointer pour cette personne."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return role_of(request) in (
            Role.OWNER,
            Role.PLANNER,
            Role.TEAM_LEAD,
            Role.STAFF,
        )


def _check_target(request: Request, pk: str, *, absent: bool = False) -> Assignment:
    assignment: Assignment = generics.get_object_or_404(_assignments(), pk=pk)
    role = role_of(request)
    if role in WRITE:
        return assignment
    mine = me(request)
    if mine is None:
        raise BusinessError("forbidden", CheckPermission.message, status_code=403)
    if (
        role == Role.TEAM_LEAD
        and Assignment.objects.filter(staff=mine, reservation_id=assignment.reservation_id).exists()
    ):
        return assignment
    if role == Role.STAFF and assignment.staff_id == mine.pk and not absent:
        return assignment
    raise BusinessError("forbidden", CheckPermission.message, status_code=403)


class CheckInView(APIView):
    permission_classes = [IsTenantMember, CheckPermission]
    open_to_field_roles = True
    action = "in"

    @extend_schema(request=None, responses=AssignmentSerializer)
    def post(self, request: Request, pk: str) -> Response:
        user = request.user
        if self.action == "in":
            services.check_in(_check_target(request, pk), user=user)  # type: ignore[arg-type]
        elif self.action == "out":
            services.check_out(_check_target(request, pk), user=user)  # type: ignore[arg-type]
        else:
            services.mark_absent(
                _check_target(request, pk, absent=True),
                user=user,  # type: ignore[arg-type]
                note=str(request.data.get("note", "")),
            )
        return Response(AssignmentSerializer(_assignments().get(pk=pk)).data)


class TaskListView(generics.ListCreateAPIView[StaffTask]):
    permission_classes = PERMISSIONS
    serializer_class = TaskSerializer
    pagination_class = None

    def get_queryset(self) -> QuerySet[StaffTask]:
        if getattr(self, "swagger_fake_view", False):
            return StaffTask.all_tenants.none()
        tasks = StaffTask.objects.select_related("staff", "reservation", "done_by", "validated_by")
        params = self.request.query_params
        if params.get("reservation"):
            tasks = tasks.filter(reservation_id=params["reservation"])
        if params.get("staff"):
            tasks = tasks.filter(staff__pk=params["staff"])
        if params.get("status") in StaffTask.Status.values:
            tasks = tasks.filter(status=params["status"])
        # « Tâches » of the staff screen (§7): by person, the coming events first.
        tasks = tasks.exclude(reservation__status="cancelled").order_by(
            "staff__full_name", "reservation__event_start", "created_at"
        )
        return tasks

    def perform_create(self, serializer: TaskSerializer) -> None:  # type: ignore[override]
        task = serializer.save(created_by=self.request.user)
        services.notify_new_task(task)


class TaskDetailView(APIView):
    """PATCH status / comment: the assigned person (with an account) or owner and planner."""

    permission_classes = [IsTenantMember, CheckPermission]
    open_to_field_roles = True

    def _task(self, request: Request, pk: str) -> StaffTask:
        task: StaffTask = generics.get_object_or_404(
            StaffTask.objects.select_related("staff", "reservation"), pk=pk
        )
        if role_of(request) not in WRITE:
            mine = me(request)
            if mine is None or task.staff_id != mine.pk:
                raise BusinessError("forbidden", "Cette tâche n’est pas la vôtre.", status_code=403)
        return task

    @extend_schema(request=TaskSerializer, responses=TaskSerializer)
    def patch(self, request: Request, pk: str) -> Response:
        """« Faite » / « À faire » by the person or for them; validation has its own action."""
        task = self._task(request, pk)
        user = request.user
        comment = request.data.get("comment")
        target = request.data.get("status")
        if target == StaffTask.Status.DONE:
            services.mark_done(task, user=user, comment=comment)  # type: ignore[arg-type]
        elif target == StaffTask.Status.TODO:
            if task.status == StaffTask.Status.VALIDATED and role_of(request) not in WRITE:
                raise BusinessError("invalid", "Cette tâche est validée : elle ne change plus.")
            services.reopen(task, user=user)  # type: ignore[arg-type]
        elif target is not None:
            raise BusinessError("invalid", "Statut inconnu.")
        if comment is not None and target != StaffTask.Status.DONE:
            task.comment = str(comment)[:2000]
            task.save(update_fields=["comment", "updated_at"])
        return Response(TaskSerializer(task).data)


class TaskReviewView(APIView):
    """Owner and planner: « Valider » a done task, or « Renvoyer » it with a reason."""

    permission_classes = PERMISSIONS
    action = "validate"

    @extend_schema(request=None, responses=TaskSerializer)
    def post(self, request: Request, pk: str) -> Response:
        if role_of(request) not in WRITE:
            raise BusinessError(
                "forbidden", "Seuls le propriétaire et le planner valident.", status_code=403
            )
        task: StaffTask = generics.get_object_or_404(
            StaffTask.objects.select_related("staff", "reservation"), pk=pk
        )
        if self.action == "validate":
            services.validate_task(task, user=request.user)  # type: ignore[arg-type]
        else:
            reason = str(request.data.get("reason", "")).strip()
            if not reason:
                raise BusinessError(
                    "invalid", "Dites ce qui reste à faire.", {"reason": ["Obligatoire."]}
                )
            services.reopen(task, user=request.user, reason=reason)  # type: ignore[arg-type]
        return Response(TaskSerializer(task).data)


class TaskPhotoView(TaskDetailView):
    parser_classes = [MultiPartParser]

    @extend_schema(responses=TaskSerializer)
    def post(self, request: Request, pk: str) -> Response:
        from django.core.files.base import ContentFile

        task = self._task(request, pk)
        upload = request.FILES.get("file")
        if upload is None:
            raise BusinessError("invalid", "Choisissez une photo.", {"file": ["Obligatoire."]})
        content = upload.read()
        if images.sniff(content) == "svg":
            raise BusinessError("invalid", "Choisissez une photo (JPEG, PNG ou WebP).")
        processed = images.process_photo(content)
        task.photo.save(f"photo.{processed.extension}", ContentFile(processed.content), save=True)
        return Response(TaskSerializer(task).data)


# --- « Mes missions » ----------------------------------------------------------------------------


class MyMissionsView(APIView):
    """The signed-in member's missions (§7 « Mes missions »): the last 14 days and the next 30,
    each with its `state` (upcoming, in_progress, done)."""

    permission_classes = [IsTenantMember]
    open_to_field_roles = True

    def get(self, request: Request) -> Response:
        mine = me(request)
        if mine is None:
            return Response({"staff": None, "missions": []})
        tz = _tz()
        start = datetime.combine(_today(), time.min, tzinfo=tz)
        role = role_of(request)
        now = timezone.now()
        missions = []
        for a in (
            _assignments()
            .filter(
                staff=mine,
                end__gte=start - timedelta(days=14),
                start__lt=start + timedelta(days=31),
            )
            .exclude(reservation__status="cancelled")
            .order_by("start")
        ):
            reservation = a.reservation
            place = reservation.address or reservation.venue
            team = list(
                Assignment.objects.filter(reservation=reservation)
                .exclude(staff=mine)
                .select_related("staff", "attendance")
            )
            missions.append(
                {
                    **AssignmentSerializer(a).data,
                    "kind": "mission",
                    "state": services.mission_state(a, now),
                    "client": reservation.client.name,
                    "client_phone": reservation.client.phone,
                    "venue": reservation.venue,
                    "address": reservation.address,
                    "maps_url": (
                        "https://www.google.com/maps/search/?api=1&query="
                        + urllib.parse.quote(place)
                        if place
                        else None
                    ),
                    "equipment": [
                        {"label": line.label, "quantity": line.quantity}
                        for line in reservation.lines.filter(
                            kind__in=("rental", "sale", "pack")
                        ).order_by("position")
                    ],
                    "tasks": TaskSerializer(
                        StaffTask.objects.filter(staff=mine, reservation=reservation), many=True
                    ).data,
                    # The team lead checks his team in (§12).
                    "team": (
                        [
                            {
                                "assignment": str(other.pk),
                                "name": other.staff.full_name,
                                "role": other.role,
                                "attendance": getattr(
                                    getattr(other, "attendance", None), "status", None
                                ),
                            }
                            for other in team
                        ]
                        if role in (Role.TEAM_LEAD, Role.OWNER, Role.PLANNER)
                        else []
                    ),
                }
            )
        missions += _task_cards(mine, missions, start, now)
        missions.sort(key=lambda m: m["start"])
        return Response(
            {"staff": {"id": str(mine.pk), "name": mine.full_name}, "missions": missions}
        )


def _task_cards(
    mine: StaffMember, missions: list[dict[str, Any]], start: datetime, now: datetime
) -> list[dict[str, Any]]:
    """Tasks given to the person on an event where they have no mission (feedback 17/11/2026:
    « une tâche donnée doit apparaître ») — one card per event, shown like a mission: where,
    when, the tasks to tick. No check-in: there is no mission to clock."""
    covered = {str(m["reservation"]) for m in missions}
    cards: dict[str, dict[str, Any]] = {}
    tasks = (
        StaffTask.objects.filter(
            staff=mine,
            reservation__event_start__gte=start - timedelta(days=14),
            reservation__event_start__lt=start + timedelta(days=31),
        )
        .exclude(reservation__status="cancelled")
        .select_related("reservation", "reservation__client", "staff")
        .order_by("reservation__event_start", "created_at")
    )
    for task in tasks:
        reservation = task.reservation
        key = str(reservation.pk)
        if key in covered:
            continue
        if key not in cards:
            place = reservation.address or reservation.venue
            end = reservation.event_end or reservation.event_start
            cards[key] = {
                "id": f"tasks-{reservation.pk}",
                "kind": "tasks",
                "staff": str(mine.pk),
                "staff_name": mine.full_name,
                "staff_position": mine.position,
                "reservation": key,
                "reservation_number": reservation.number,
                "reservation_title": reservation.title,
                "step": Assignment.Step.EVENT,
                "step_label": "Tâches",
                "role": "",
                # Same format as the missions' dates (API strings), so they sort together.
                "start": serializers.DateTimeField().to_representation(reservation.event_start),
                "end": serializers.DateTimeField().to_representation(end),
                "attendance": None,
                "conflicts": [],
                "state": "done" if end < now else "upcoming",
                "_end": end,
                "client": reservation.client.name,
                "client_phone": reservation.client.phone,
                "venue": reservation.venue,
                "address": reservation.address,
                "maps_url": (
                    "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(place)
                    if place
                    else None
                ),
                "equipment": [],
                "tasks": [],
                "team": [],
            }
        cards[key]["tasks"].append(TaskSerializer(task).data)
    # Still to do on a past event: the card stays « en cours » so it is not forgotten.
    for card in cards.values():
        card.pop("_end")
        if card["state"] == "done" and any(t["status"] == "todo" for t in card["tasks"]):
            card["state"] = "in_progress"
    return list(cards.values())


class MyOverviewView(APIView):
    """« Mon espace » (feedback 13/11/2026): the person's own figures; never an amount."""

    permission_classes = [IsTenantMember]
    open_to_field_roles = True

    def get(self, request: Request) -> Response:
        mine = me(request)
        if mine is None:
            return Response({"staff": None})
        return Response(
            {
                "staff": {
                    "id": str(mine.pk),
                    "name": mine.full_name,
                    "position": mine.position,
                    "department": mine.department,
                    "employee_number": mine.employee_number,
                    "photo_url": signed_url(mine.photo.name) if mine.photo else None,
                },
                **services.overview(
                    mine, with_team=role_of(request) in (Role.TEAM_LEAD, Role.OWNER, Role.PLANNER)
                ),
            }
        )


# --- Pay -----------------------------------------------------------------------------------------


def _periods() -> QuerySet[PayPeriod]:
    return PayPeriod.objects.prefetch_related("lines__staff")


class PayPeriodListView(APIView):
    permission_classes = PERMISSIONS
    pay_view = True

    @extend_schema(responses=PayPeriodSerializer(many=True))
    def get(self, request: Request) -> Response:
        return Response(PayPeriodSerializer(_periods(), many=True).data)

    @extend_schema(request=None, responses=PayPeriodSerializer)
    def post(self, request: Request) -> Response:
        try:
            start = date.fromisoformat(str(request.data.get("start")))
            end = date.fromisoformat(str(request.data.get("end")))
        except ValueError as exc:
            raise BusinessError("invalid", "Dates illisibles (AAAA-MM-JJ).") from exc
        period = services.create_period(start, end, user=request.user)  # type: ignore[arg-type]
        return Response(PayPeriodSerializer(_periods().get(pk=period.pk)).data, status=201)


class PayPeriodActionView(APIView):
    permission_classes = PERMISSIONS
    pay_view = True
    action = "refresh"

    @extend_schema(request=None, responses=PayPeriodSerializer)
    def post(self, request: Request, pk: str) -> Response:
        period: PayPeriod = generics.get_object_or_404(PayPeriod.objects.all(), pk=pk)
        if self.action == "validate":
            if role_of(request) != Role.OWNER:
                raise BusinessError(
                    "forbidden", "Seul le propriétaire valide la paie.", status_code=403
                )
            services.validate(period, user=request.user, request=request)  # type: ignore[arg-type]
        else:
            services.refresh(period)
        return Response(PayPeriodSerializer(_periods().get(pk=pk)).data)


class PayLineView(APIView):
    """PATCH bonuses / advances (draft) · POST /pay (validated) · GET /statement (PDF)."""

    permission_classes = PERMISSIONS
    pay_view = True

    def _line(self, pk: str) -> PayLine:
        line: PayLine = generics.get_object_or_404(
            PayLine.objects.select_related("period", "staff"), pk=pk
        )
        return line

    @extend_schema(request=None, responses=PayLineSerializer)
    def patch(self, request: Request, pk: str) -> Response:
        line = self._line(pk)
        try:
            bonuses = int(request.data.get("bonuses", line.bonuses))
            advances = int(request.data.get("advances", line.advances))
        except (TypeError, ValueError) as exc:
            raise BusinessError("invalid", "Montants illisibles.") from exc
        if bonuses < 0 or advances < 0:
            raise BusinessError("invalid", "Les montants sont positifs.")
        return Response(
            PayLineSerializer(services.update_line(line, bonuses=bonuses, advances=advances)).data
        )


class PayLinePayView(PayLineView):
    @extend_schema(request=None, responses=PayLineSerializer)
    def post(self, request: Request, pk: str) -> Response:
        method = str(request.data.get("method", "cash"))
        try:
            paid_at = date.fromisoformat(str(request.data.get("paid_at") or _today()))
        except ValueError as exc:
            raise BusinessError("invalid", "Date illisible.") from exc
        line = services.pay_line(
            self._line(pk), method=method, paid_at=paid_at, user=request.user, request=request  # type: ignore[arg-type]
        )
        return Response(PayLineSerializer(line).data)


class PayStatementView(PayLineView):
    """« Relevé de rémunération » PDF (§7) — not a legal payslip."""

    @extend_schema(responses={200: OpenApiResponse(description="PDF")})
    def get(self, request: Request, pk: str) -> HttpResponse:
        line = self._line(pk)
        organization = require_current_organization()
        branding = branding_services.get_branding()
        attendances = Attendance.objects.filter(
            staff=line.staff,
            date__range=(line.period.start, line.period.end),
        ).select_related("assignment__reservation")
        html = render_to_string(
            "staff/statement.html",
            {
                "agency": branding.trade_name or organization.name,
                "logo": branding_services.logo_data_uri(),
                "line": line,
                "staff": line.staff,
                "period": f"Du {long_date(line.period.start.isoformat())} au "
                f"{long_date(line.period.end.isoformat())}",
                "rate": money(line.staff.pay_rate),
                "base": money(line.base),
                "bonuses": money(line.bonuses),
                "advances": money(line.advances),
                "total": money(line.total),
                "paid": long_date(line.paid_at.isoformat()) if line.paid_at else None,
                "rows": [
                    {
                        "date": long_date(a.date.isoformat()),
                        "mission": a.assignment.reservation.number if a.assignment else "—",
                        "status": a.get_status_display(),
                        "hours": f"{a.hours:.2f}".replace(".", ","),
                    }
                    for a in attendances
                ],
                "fonts": {
                    "m400": rendering.asset_url("fonts/montserrat-latin-400-normal.woff"),
                    "m700": rendering.asset_url("fonts/montserrat-latin-700-normal.woff"),
                },
            },
        )
        response = HttpResponse(
            rendering.html_to_pdf(html, str(organization.pk)), content_type="application/pdf"
        )
        name = line.staff.full_name.replace(" ", "-").lower()
        response["Content-Disposition"] = f'attachment; filename="releve-{name}.pdf"'
        return response


class StaffBadgePreviewView(APIView):
    """One card as a PNG: `?design=&staff=` (the first active member by default)."""

    permission_classes = PERMISSIONS

    @extend_schema(responses={200: OpenApiResponse(description="PNG")})
    def get(self, request: Request) -> HttpResponse:
        from . import badges

        people = StaffMember.objects.filter(is_active=True).order_by("full_name")
        if request.query_params.get("staff"):
            people = StaffMember.objects.filter(pk=request.query_params["staff"], is_deleted=False)
        person = people.first()
        if person is None:
            raise BusinessError("invalid", "Ajoutez d’abord une personne.")
        image = badges.preview(person, request.query_params.get("design", "classique"))
        response = HttpResponse(image, content_type="image/png")
        response["Cache-Control"] = "private, max-age=60"
        return response


class StaffBadgesView(APIView):
    """Badges PDF (credit-card size, 8 per A4): `?ids=a,b` or every active member."""

    permission_classes = PERMISSIONS

    @extend_schema(responses={200: OpenApiResponse(description="PDF")})
    def get(self, request: Request) -> HttpResponse:
        from . import badges

        people = StaffMember.objects.filter(is_active=True)
        ids = [i for i in request.query_params.get("ids", "").split(",") if i]
        if ids:
            people = StaffMember.objects.filter(pk__in=ids, is_deleted=False)
        people = people.order_by("full_name")
        if not people.exists():
            raise BusinessError("invalid", "Aucune personne à imprimer.")
        design = request.query_params.get("design", "classique")
        response = HttpResponse(badges.render(people, design), content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="badges-personnel.pdf"'
        return response


# --- « Payer la journée » (feedback 13/11/2026) ---------------------------------------------------


class DaySheetView(APIView):
    """`?date=&reservation=`: who worked that day, what we owe them, what is already paid."""

    permission_classes = PERMISSIONS
    pay_view = True

    def get(self, request: Request) -> Response:
        try:
            day = date.fromisoformat(request.query_params.get("date") or _today().isoformat())
        except ValueError as exc:
            raise BusinessError("invalid", "Date illisible (AAAA-MM-JJ).") from exc
        reservation = None
        if request.query_params.get("reservation"):
            reservation = generics.get_object_or_404(
                Reservation.objects.all(), pk=request.query_params["reservation"]
            )
        tz = _tz()
        first = datetime.combine(day, time.min, tzinfo=tz)
        events = (
            Reservation.objects.filter(
                assignments__start__lt=first + timedelta(days=1), assignments__end__gt=first
            )
            .exclude(status="cancelled")
            .distinct()
            .order_by("event_start")
        )
        return Response(
            {
                "date": day,
                "reservations": [
                    {"id": str(r.pk), "number": r.number, "title": r.title} for r in events
                ],
                "rows": services.day_sheet(day, reservation),
            }
        )


class PayNowInput(serializers.Serializer[Any]):
    class Line(serializers.Serializer[Any]):
        staff = TenantPrimaryKeyRelatedField(StaffMember)
        amount = serializers.IntegerField(min_value=0)
        note = serializers.CharField(max_length=160, required=False, allow_blank=True)

    date = serializers.DateField()
    reservation = TenantPrimaryKeyRelatedField(Reservation, required=False, allow_null=True)
    method = serializers.ChoiceField(
        choices=["cash", "orange_money", "mtn_momo", "wave", "transfer", "cheque"]
    )
    lines = Line(many=True)


class StaffPaymentSerializer(serializers.ModelSerializer[StaffPayment]):
    staff_name = serializers.CharField(source="staff.full_name", read_only=True)
    reservation_number = serializers.CharField(
        source="reservation.number", read_only=True, default=None
    )

    class Meta:
        model = StaffPayment
        fields = [
            "id",
            "staff",
            "staff_name",
            "reservation",
            "reservation_number",
            "date",
            "amount",
            "method",
            "note",
        ]
        read_only_fields = fields


class StaffPaymentListView(APIView):
    """GET `?from=&to=` (the 30 last days by default) · POST: pay several people at once."""

    permission_classes = PERMISSIONS
    pay_view = True

    @extend_schema(responses=StaffPaymentSerializer(many=True))
    def get(self, request: Request) -> Response:
        try:
            end = date.fromisoformat(request.query_params.get("to") or _today().isoformat())
            start = date.fromisoformat(
                request.query_params.get("from") or (end - timedelta(days=30)).isoformat()
            )
        except ValueError as exc:
            raise BusinessError("invalid", "Date illisible (AAAA-MM-JJ).") from exc
        rows = StaffPayment.objects.filter(date__range=(start, end)).select_related(
            "staff", "reservation"
        )
        return Response(StaffPaymentSerializer(rows, many=True).data)

    @extend_schema(request=PayNowInput, responses=StaffPaymentSerializer(many=True))
    def post(self, request: Request) -> Response:
        data = PayNowInput(data=request.data)
        data.is_valid(raise_exception=True)
        payments = services.pay_now(
            data.validated_data["date"],
            data.validated_data["lines"],
            method=data.validated_data["method"],
            reservation=data.validated_data.get("reservation"),
            user=request.user,  # type: ignore[arg-type]
            request=request,
        )
        return Response(StaffPaymentSerializer(payments, many=True).data, status=201)


METHOD_LABELS = {
    "cash": "Espèces",
    "orange_money": "Orange Money",
    "mtn_momo": "MTN MoMo",
    "wave": "Wave",
    "transfer": "Virement",
    "cheque": "Chèque",
}


def _hours(value: Decimal) -> str:
    return f"{value:.2f}".replace(".", ",").removesuffix(",00") + " h" if value else "—"


class DayPaySheetView(APIView):
    """`?date=&reservation=` : « Feuille de paie du jour » (feedback 15/11/2026), one PDF with
    everyone paid that day (or for that event), their amount and a signature column."""

    permission_classes = PERMISSIONS
    pay_view = True

    @extend_schema(responses={200: OpenApiResponse(description="PDF")})
    def get(self, request: Request) -> HttpResponse:
        try:
            day = date.fromisoformat(request.query_params.get("date") or _today().isoformat())
        except ValueError as exc:
            raise BusinessError("invalid", "Date illisible (AAAA-MM-JJ).") from exc
        payments = StaffPayment.objects.filter(date=day).select_related("staff", "reservation")
        reservation = None
        if request.query_params.get("reservation"):
            reservation = generics.get_object_or_404(
                Reservation.objects.all(), pk=request.query_params["reservation"]
            )
            payments = payments.filter(reservation=reservation)
        payments = payments.order_by("staff__full_name", "created_at")
        if not payments:
            raise BusinessError(
                "not_found",
                "Aucun paiement enregistré ce jour-là : payez d’abord la journée.",
                status_code=404,
            )
        # Missions of each person that day: their events, and hours checked in (else planned).
        first = datetime.combine(day, time.min, tzinfo=_tz())
        hours: dict[Any, Decimal] = {}
        events: dict[Any, dict[Any, str]] = {}
        for assignment in (
            Assignment.objects.filter(
                staff_id__in={p.staff_id for p in payments},
                start__lt=first + timedelta(days=1),
                end__gt=first,
            )
            .exclude(reservation__status="cancelled")
            .select_related("reservation", "attendance")
        ):
            attendance = getattr(assignment, "attendance", None)
            if attendance is not None and attendance.status == Attendance.Status.ABSENT:
                continue
            worked = (
                attendance.hours
                if attendance is not None and attendance.hours
                else Decimal((assignment.end - assignment.start).total_seconds()) / 3600
            )
            hours[assignment.staff_id] = hours.get(assignment.staff_id, Decimal(0)) + worked
            reservation_of = assignment.reservation
            events.setdefault(assignment.staff_id, {})[
                reservation_of.pk
            ] = f"{reservation_of.number} · {reservation_of.title}"
        organization = require_current_organization()
        branding = branding_services.get_branding()
        html = render_to_string(
            "staff/day_sheet.html",
            {
                "agency": branding.trade_name or organization.name,
                "logo": branding_services.logo_data_uri(),
                "day_label": long_date(day.isoformat()),
                "scope": (
                    f"{reservation.number} · {reservation.title}"
                    if reservation
                    else "Tous les événements du jour"
                ),
                "count": len({p.staff_id for p in payments}),
                "printed": timezone.localtime(timezone.now(), _tz()).strftime("%d/%m/%Y à %H:%M"),
                "rows": [
                    {
                        "name": p.staff.full_name,
                        "position": p.staff.position,
                        "number": p.staff.employee_number,
                        "note": p.note,
                        "event": (
                            f"{p.reservation.number} · {p.reservation.title}"
                            if p.reservation
                            else " / ".join(events.get(p.staff_id, {}).values()) or "—"
                        ),
                        "hours": _hours(hours.get(p.staff_id, Decimal(0))),
                        "method": METHOD_LABELS.get(p.method, p.method),
                        "mobile_money": (
                            p.staff.mobile_money
                            if p.method in ("orange_money", "mtn_momo", "wave")
                            else ""
                        ),
                        "amount": money(p.amount),
                    }
                    for p in payments
                ],
                "total": money(sum(p.amount for p in payments)),
                "fonts": {
                    "m400": rendering.asset_url("fonts/montserrat-latin-400-normal.woff"),
                    "m700": rendering.asset_url("fonts/montserrat-latin-700-normal.woff"),
                },
            },
        )
        response = HttpResponse(
            rendering.html_to_pdf(html, str(organization.pk)), content_type="application/pdf"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="feuille-de-paie-{day.isoformat()}.pdf"'
        )
        return response


class PublicBadgeView(PublicAPIView):
    """What the badge QR opens (feedback 13/11/2026): « Badge valide » for a member still on the
    team, with the agency, photo, name and position — nothing private (no phone, no pay)."""

    @extend_schema(responses={200: OpenApiResponse(description="Badge vérifié")})
    def get(self, request: Request, token: str) -> Response:
        from core.tenant import tenant_context

        staff = services.badge_from_token(token)
        if staff is None:
            raise BusinessError("not_found", "Badge non reconnu.", status_code=404)
        with tenant_context(staff.organization):
            branding = branding_services.get_branding()
            response = Response(
                {
                    "valid": staff.is_active,
                    "name": staff.full_name,
                    "position": staff.position,
                    "department": staff.department,
                    "number": services.ensure_employee_number(staff),
                    "kind": staff.get_kind_display(),
                    "agency": branding.trade_name or staff.organization.name,
                    "logo": branding_services.logo_data_uri(),
                    "photo_url": signed_url(staff.photo.name) if staff.photo else None,
                }
            )
        response["X-Robots-Tag"] = "noindex"
        response["Referrer-Policy"] = "no-referrer"
        return response
