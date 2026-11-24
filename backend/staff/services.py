"""Staff business rules (docs/specs/reservations-stock.md §7)."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from accounts.models import User
from core import audit
from core.exceptions import BusinessError
from core.tenant import require_current_organization
from organizations.timezones import org_tz

from . import payroll
from .models import (
    Assignment,
    Attendance,
    PayLine,
    PayPeriod,
    PayrollSettings,
    StaffMember,
    StaffPayment,
    StaffTask,
)

LATE_AFTER = timedelta(minutes=15)  # a check-in later than the start + 15 min is « en retard »
STEP_HOURS = {"delivery": 3, "teardown": 3, "pickup": 3, "return": 2, "setup": 4}
MONTH_HOURS = Decimal("173.33")  # 40 h × 52 / 12: hourly cost of a monthly salary
PAYABLE = (Attendance.Status.PRESENT, Attendance.Status.LATE)


def today() -> date:
    return timezone.now().astimezone(org_tz(require_current_organization())).date()


# --- Assignments ---------------------------------------------------------------------------------


def step_window(reservation: Any, step: str) -> tuple[datetime, datetime]:
    """When a step keeps someone busy: from its time for a few hours, the event from start to
    end, « toute la réservation » from the first to the last logistic time."""
    if step == Assignment.Step.ALL:
        first = reservation.delivery_at or reservation.setup_at or reservation.event_start
        last = (
            reservation.return_at
            or reservation.pickup_at
            or reservation.teardown_at
            or reservation.event_end
        )
        return first, last
    if step == Assignment.Step.EVENT:
        return reservation.event_start, reservation.event_end
    moment = getattr(reservation, f"{step}_at", None)
    if moment is None:
        raise BusinessError(
            "invalid",
            "Cette étape n’a pas d’heure sur la réservation : ajoutez-la d’abord.",
            {"step": ["Heure manquante."]},
        )
    end = moment + timedelta(hours=STEP_HOURS.get(step, 3))
    if step == Assignment.Step.SETUP:
        end = min(end, reservation.event_start) if reservation.event_start > moment else end
    return moment, end


@dataclass(frozen=True)
class Conflict:
    kind: str  # « overlap »: already busy; « absent »: marked absent that day
    message: str
    reservation: str | None


def conflicts(
    staff: StaffMember, start: datetime, end: datetime, *, exclude: Any = None
) -> list[Conflict]:
    """§7: « alerte si une personne est déjà affectée au même moment ou absente »."""
    tz = org_tz(require_current_organization())
    found = []
    busy = (
        Assignment.objects.filter(staff=staff, start__lt=end, end__gt=start)
        .exclude(pk=exclude)
        .exclude(reservation__status="cancelled")
        .select_related("reservation")
    )
    for other in busy:
        when = timezone.localtime(other.start, tz)
        found.append(
            Conflict(
                "overlap",
                f"{staff.full_name} est déjà sur {other.reservation.number} "
                f"le {when:%d/%m} à {when:%H:%M}.",
                str(other.reservation_id),
            )
        )
    days = {
        timezone.localtime(start, tz).date() + timedelta(days=offset)
        for offset in range(
            (timezone.localtime(end, tz).date() - timezone.localtime(start, tz).date()).days + 1
        )
    }
    for absence in Attendance.objects.filter(
        staff=staff, status=Attendance.Status.ABSENT, date__in=days
    ):
        found.append(
            Conflict(
                "absent",
                f"{staff.full_name} est absent(e) le {absence.date:%d/%m}.",
                None,
            )
        )
    return found


@transaction.atomic
def assign(
    reservation: Any, staff: StaffMember, *, step: str, role: str, user: User
) -> tuple[Assignment, list[Conflict]]:
    if reservation.status == "cancelled":
        raise BusinessError("invalid", "Cette réservation est annulée.")
    if not staff.is_active:
        raise BusinessError("invalid", f"{staff.full_name} n’est plus actif(ve).")
    start, end = step_window(reservation, step)
    if Assignment.objects.filter(reservation=reservation, staff=staff, step=step).exists():
        raise BusinessError("invalid", f"{staff.full_name} est déjà affecté(e) à cette étape.")
    found = conflicts(staff, start, end)
    assignment = Assignment.objects.create(
        staff=staff,
        reservation=reservation,
        step=step,
        role=role.strip() or staff.position,
        start=start,
        end=end,
        created_by=user,
    )
    notify_assignment(assignment)
    return assignment, found


def _when(instant: datetime) -> str:
    local = timezone.localtime(instant, org_tz(require_current_organization()))
    return local.strftime("%d/%m à %H:%M")


def notify_assignment(assignment: Assignment) -> None:
    """Push (13/11/2026): the person learns of a new mission on their phone."""
    from notifications import push

    if assignment.staff.user_id is None:
        return
    push.notify(
        [assignment.staff.user_id],
        title="Nouvelle mission",
        body=f"{assignment.reservation.title} · {assignment.get_step_display()} "
        f"le {_when(assignment.start)}",
        url="/mes-missions",
        kind="mission",
        tag=f"assignment-{assignment.pk}",
    )


def notify_new_task(task: Any) -> None:
    from notifications import push

    if task.staff.user_id is None:
        return
    push.notify(
        [task.staff.user_id],
        title="Nouvelle tâche",
        body=f"{task.title} · {task.reservation.title}",
        url="/mes-missions",
        kind="task",
        tag=f"task-{task.pk}",
    )


def follow_reservation(reservation: Any) -> None:
    """New dates (edited or dragged in the calendar): the assignments follow."""
    for assignment in Assignment.objects.filter(reservation=reservation):
        try:
            start, end = step_window(reservation, assignment.step)
        except BusinessError:
            continue
        if (start, end) != (assignment.start, assignment.end):
            assignment.start, assignment.end = start, end
            assignment.save(update_fields=["start", "end", "updated_at"])


# --- Attendance ----------------------------------------------------------------------------------


def _attendance(assignment: Assignment, user: User) -> Attendance:
    attendance: Attendance
    attendance, _ = Attendance.objects.get_or_create(
        assignment=assignment,
        defaults={
            "staff": assignment.staff,
            "date": timezone.localtime(
                assignment.start, org_tz(require_current_organization())
            ).date(),
            "recorded_by": user,
        },
    )
    return attendance


def _hours(attendance: Attendance) -> Decimal:
    if not (attendance.check_in and attendance.check_out):
        return Decimal(0)
    seconds = max(0.0, (attendance.check_out - attendance.check_in).total_seconds())
    return (Decimal(seconds) / 3600).quantize(Decimal("0.01"), ROUND_HALF_UP)


@transaction.atomic
def check_in(assignment: Assignment, *, user: User, at: datetime | None = None) -> Attendance:
    at = at or timezone.now()
    attendance = _attendance(assignment, user)
    attendance.check_in = at
    attendance.status = (
        Attendance.Status.LATE if at > assignment.start + LATE_AFTER else Attendance.Status.PRESENT
    )
    attendance.recorded_by = user
    attendance.hours = _hours(attendance)
    attendance.save()
    if attendance.status == Attendance.Status.LATE:
        from notifications import flow

        flow.attendance(assignment, title="Arrivée en retard", actor=user)
    return attendance


@transaction.atomic
def check_out(assignment: Assignment, *, user: User, at: datetime | None = None) -> Attendance:
    attendance = _attendance(assignment, user)
    if attendance.check_in is None:
        raise BusinessError("invalid", "Pointez d’abord l’arrivée.")
    at = at or timezone.now()
    if at <= attendance.check_in:
        raise BusinessError("invalid", "Le départ doit suivre l’arrivée.")
    attendance.check_out = at
    attendance.hours = _hours(attendance)
    attendance.recorded_by = user
    attendance.save()
    return attendance


@transaction.atomic
def mark_absent(assignment: Assignment, *, user: User, note: str = "") -> Attendance:
    attendance = _attendance(assignment, user)
    attendance.status = Attendance.Status.ABSENT
    attendance.check_in = attendance.check_out = None
    attendance.hours = Decimal(0)
    attendance.note = note.strip()
    attendance.recorded_by = user
    attendance.save()
    from notifications import flow

    flow.attendance(assignment, title="Absence signalée", actor=user)
    return attendance


# --- Cost of a person (pay and profitability) ----------------------------------------------------


def hourly_cost(staff: StaffMember) -> Decimal:
    if staff.pay_mode == StaffMember.PayMode.HOURLY:
        return Decimal(staff.pay_rate)
    if staff.pay_mode == StaffMember.PayMode.DAILY:
        return Decimal(staff.pay_rate) / 8
    if staff.pay_mode == StaffMember.PayMode.MONTHLY:
        return Decimal(staff.pay_rate) / MONTH_HOURS
    return Decimal(0)  # missions are paid per mission, not per hour


def reservation_cost(reservation: Any) -> int:
    """§6.4: staff on an event at the pro rata of their hours — worked hours when checked in,
    planned hours otherwise; a mission rate counts once, a day rate once per day."""
    total = Decimal(0)
    missions: set[str] = set()
    days: set[tuple[str, date]] = set()
    for assignment in Assignment.objects.filter(reservation=reservation).select_related(
        "staff", "attendance"
    ):
        staff = assignment.staff
        attendance = getattr(assignment, "attendance", None)
        if attendance is not None and attendance.status == Attendance.Status.ABSENT:
            continue
        if staff.pay_mode == StaffMember.PayMode.MISSION:
            if str(staff.pk) not in missions:
                missions.add(str(staff.pk))
                total += staff.pay_rate
            continue
        if staff.pay_mode == StaffMember.PayMode.DAILY:
            day = timezone.localtime(assignment.start).date()
            if (str(staff.pk), day) not in days:
                days.add((str(staff.pk), day))
                total += staff.pay_rate
            continue
        hours = (
            attendance.hours
            if attendance is not None and attendance.hours
            else Decimal((assignment.end - assignment.start).total_seconds()) / 3600
        )
        total += hourly_cost(staff) * hours
    return int(total.quantize(Decimal(1), ROUND_HALF_UP))


# --- Pay -----------------------------------------------------------------------------------------


def _months(start: date, end: date) -> Decimal:
    """Whole calendar months when the period is made of them, else days ÷ 30."""
    last_day = calendar.monthrange(end.year, end.month)[1]
    if start.day == 1 and end.day == last_day:
        return Decimal((end.year - start.year) * 12 + end.month - start.month + 1)
    return Decimal((end - start).days + 1) / 30


def compute_line(line: PayLine) -> PayLine:
    period, staff = line.period, line.staff
    worked = Attendance.objects.filter(
        staff=staff, date__range=(period.start, period.end), status__in=PAYABLE
    ).select_related("assignment")
    line.days = len({a.date for a in worked})
    line.missions = len({a.assignment.reservation_id for a in worked if a.assignment})
    line.hours = sum((a.hours for a in worked), Decimal(0))
    rate = Decimal(staff.pay_rate)
    base = {
        StaffMember.PayMode.MONTHLY: rate * _months(period.start, period.end),
        StaffMember.PayMode.DAILY: rate * line.days,
        StaffMember.PayMode.MISSION: rate * line.missions,
        StaffMember.PayMode.HOURLY: rate * Decimal(line.hours),
    }[StaffMember.PayMode(staff.pay_mode)]
    line.base = int(base.quantize(Decimal(1), ROUND_HALF_UP))
    line.already_paid = int(
        StaffPayment.objects.filter(staff=staff, date__range=(period.start, period.end)).aggregate(
            total=Sum("amount")
        )["total"]
        or 0
    )
    items = list(line.items or [])
    line.bonuses = sum(int(i["amount"]) for i in items if i["kind"] == payroll.GAIN)
    line.advances = sum(int(i["amount"]) for i in items if i["kind"] == payroll.DEDUCTION)
    slip = payroll.compute(
        line.base,
        items,
        declared=staff.declared,
        settings=payroll_settings(months=_months(period.start, period.end)),
    )
    line.gross, line.net = slip.gross, slip.net
    line.slip = payroll.summary(slip)
    line.total = max(0, slip.net - line.already_paid)
    return line


def get_payroll_settings() -> PayrollSettings:
    found = PayrollSettings.objects.get_or_create(organization=require_current_organization())
    settings: PayrollSettings = found[0]
    return settings


def payroll_settings(months: Decimal = Decimal(1)) -> payroll.Settings:
    stored = get_payroll_settings()
    return payroll.Settings(
        enabled=stored.contributions_enabled,
        accident_rate=Decimal(stored.accident_rate),
        months=months,
    )


def year_to_date(line: PayLine) -> dict[str, int]:
    """Cumuls of the year on the slip: validated or paid periods of the same year, this one
    included."""
    stored = PayLine.objects.filter(
        staff=line.staff,
        period__start__year=line.period.start.year,
        period__start__lte=line.period.start,
    ).exclude(period__status=PayPeriod.Status.DRAFT)
    lines = list(stored) if line.period.status != PayPeriod.Status.DRAFT else [*stored, line]
    taxes = ("irpp", "cac")
    return {
        "gross": sum(item.gross for item in lines),
        "withheld": sum(int((item.slip or {}).get("withheld", 0)) for item in lines),
        "taxes": sum(
            int(c["amount"])
            for item in lines
            for c in (item.slip or {}).get("employee", [])
            if c["code"] in taxes
        ),
        "net": sum(item.net for item in lines),
    }


@transaction.atomic
def create_period(start: date, end: date, *, user: User) -> PayPeriod:
    if end < start:
        raise BusinessError("invalid", "La fin précède le début.", {"end": ["Date incohérente."]})
    if PayPeriod.objects.filter(start__lte=end, end__gte=start).exists():
        raise BusinessError("invalid", "Une période de paie couvre déjà ces dates.")
    period: PayPeriod = PayPeriod.objects.create(start=start, end=end, created_by=user)
    refresh(period)
    audit.record("pay_period.created", period, changes={"start": str(start), "end": str(end)})
    return period


def _draft(period: PayPeriod) -> None:
    if period.status != PayPeriod.Status.DRAFT:
        raise BusinessError("pay_period_locked", "Cette période est validée : elle ne change plus.")


@transaction.atomic
def refresh(period: PayPeriod) -> PayPeriod:
    """(Re)compute every line from attendance; keeps bonuses and advances already typed."""
    period = PayPeriod.objects.select_for_update().get(pk=period.pk)
    _draft(period)
    existing = {line.staff_id: line for line in period.lines.select_related("staff")}
    for staff in StaffMember.objects.filter(is_active=True):
        line = existing.get(staff.pk) or PayLine(
            period=period, staff=staff, organization=period.organization
        )
        line.period, line.staff = period, staff
        compute_line(line)
        # Salaried people always have their line, even without salary typed yet (to set it).
        if line.pk or line.base or staff.pay_mode == StaffMember.PayMode.MONTHLY:
            line.save()
    return period


@transaction.atomic
def update_line(line: PayLine, *, items: list[dict[str, Any]]) -> PayLine:
    """The named lines of the slip (bonuses, allowances, overtime, advances, absences…)."""
    _draft(line.period)
    try:
        line.items = payroll.clean_items(items)
    except ValueError as exc:
        raise BusinessError("invalid", str(exc)) from exc
    compute_line(line)
    line.save()
    return line


@transaction.atomic
def validate(period: PayPeriod, *, user: User, request: Any = None) -> PayPeriod:
    period = PayPeriod.objects.select_for_update().get(pk=period.pk)
    _draft(period)
    refresh(period)
    period.status = PayPeriod.Status.VALIDATED
    period.validated_at = timezone.now()
    period.validated_by = user
    period.save()
    audit.record("pay_period.validated", period, request=request)
    return period


@transaction.atomic
def pay_line(
    line: PayLine, *, method: str, paid_at: date, user: User, request: Any = None
) -> PayLine:
    """The payment creates the expense « Salaires et journaliers » (§6.1, §7)."""
    from finance.defaults import ensure_expense_categories
    from finance.models import Expense, ExpenseCategory

    line = PayLine.objects.select_for_update().select_related("period", "staff").get(pk=line.pk)
    if line.period.status == PayPeriod.Status.DRAFT:
        raise BusinessError(
            "invalid", "Faites valider la période par le propriétaire avant de payer."
        )
    if line.paid_at:
        raise BusinessError("invalid", "Cette rémunération est déjà payée.")
    if line.total <= 0:
        raise BusinessError("invalid", "Rien à payer sur cette ligne.")
    ensure_expense_categories()
    line.expense = Expense.objects.create(
        label=(
            f"Rémunération {line.staff.full_name} "
            f"({line.period.start:%d/%m}–{line.period.end:%d/%m})"
        ),
        amount=line.total,
        date=paid_at,
        category=ExpenseCategory.objects.get(name="Salaires et journaliers"),
        supplier=line.staff.full_name,
        method=method,
        is_paid=True,
        created_by=user,
    )
    line.paid_at, line.method = paid_at, method
    line.save()
    if not line.period.lines.filter(paid_at__isnull=True, total__gt=0).exists():
        PayPeriod.objects.filter(pk=line.period_id).update(status=PayPeriod.Status.PAID)
    audit.record("pay_line.paid", line, request=request, changes={"amount": line.total})
    return line


# --- Tasks: done by the person, validated by the owner or the planner ----------------------------


def mark_done(task: Any, *, user: User, comment: str | None = None) -> Any:
    from .models import StaffTask

    if task.status == StaffTask.Status.VALIDATED:
        raise BusinessError("invalid", "Cette tâche est déjà validée.")
    task.status = StaffTask.Status.DONE
    task.done_at, task.done_by = timezone.now(), user
    task.rejection_reason = ""
    if comment is not None:
        task.comment = comment.strip()[:2000]
    task.save()
    if task.staff.user_id is not None and str(task.staff.user_id) == str(user.pk):
        # Done by the person: the owner and the planners have it to validate.
        from notifications import push

        push.notify(
            push.members_with_roles(["owner", "planner"], exclude=user.pk),
            title="Tâche faite, à valider",
            body=f"{task.title} · {task.staff.full_name}",
            url="/taches",
            kind="task",
            tag=f"task-{task.pk}",
        )
    return task


def reopen(task: Any, *, user: User, reason: str = "") -> Any:
    """Back to « à faire »: by the person (not validated yet) or sent back by the manager."""
    from .models import StaffTask

    task.status = StaffTask.Status.TODO
    task.done_at = task.done_by = task.validated_at = task.validated_by = None
    task.rejection_reason = reason.strip()[:255]
    task.save()
    if task.rejection_reason and task.staff.user_id is not None:
        from notifications import push

        push.notify(
            [task.staff.user_id],
            title="Tâche à reprendre",
            body=f"{task.title} : {task.rejection_reason}",
            url="/mes-missions",
            kind="task",
            tag=f"task-{task.pk}",
        )
    return task


def validate_task(task: Any, *, user: User) -> Any:
    from .models import StaffTask

    if task.status != StaffTask.Status.DONE:
        raise BusinessError("invalid", "Seule une tâche faite peut être validée.")
    task.status = StaffTask.Status.VALIDATED
    task.validated_at, task.validated_by = timezone.now(), user
    task.save()
    audit.record("staff_task.validated", task, changes={"title": task.title})
    if task.staff.user_id is not None and str(task.staff.user_id) != str(user.pk):
        from notifications import flow

        flow.to_person(
            task.staff.user_id,
            title="Tâche validée",
            body=f"{task.title} · {task.reservation.title}",
            url="/mes-missions",
            kind="task",
            tag=f"task-{task.pk}",
        )
    return task


# --- Paying on the spot (« Payer la journée ») ---------------------------------------------------


def day_sheet(day: date, reservation: Any = None) -> list[dict[str, Any]]:
    """Who worked that day (or is planned), what we owe them for it and what is already paid.
    Salaried staff are listed for information: their salary comes with the pay period."""
    tz = org_tz(require_current_organization())
    first = datetime.combine(day, datetime.min.time(), tzinfo=tz)
    assignments = (
        Assignment.objects.filter(start__lt=first + timedelta(days=1), end__gt=first)
        .exclude(reservation__status="cancelled")
        .select_related("staff", "reservation", "attendance")
    )
    if reservation is not None:
        assignments = assignments.filter(reservation=reservation)
    people: dict[Any, dict[str, Any]] = {}
    for assignment in assignments:
        staff = assignment.staff
        attendance = getattr(assignment, "attendance", None)
        if attendance is not None and attendance.status == Attendance.Status.ABSENT:
            status = "absent"
        elif attendance is not None and attendance.check_in:
            status = attendance.status
        else:
            status = "planned"
        hours = (
            attendance.hours
            if attendance is not None and attendance.hours
            else Decimal((assignment.end - assignment.start).total_seconds()) / 3600
        )
        row = people.setdefault(
            staff.pk,
            {
                "staff": staff,
                "reservations": {},
                "status": status,
                "hours": Decimal(0),
            },
        )
        row["reservations"][assignment.reservation_id] = assignment.reservation.number
        row["hours"] += hours if status != "absent" else 0
        if status in ("present", "late") or row["status"] == "absent":
            row["status"] = status
    rows = []
    for row in people.values():
        staff = row["staff"]
        mode = StaffMember.PayMode(staff.pay_mode)
        due = {
            StaffMember.PayMode.DAILY: Decimal(staff.pay_rate),
            StaffMember.PayMode.MISSION: Decimal(staff.pay_rate) * len(row["reservations"]),
            StaffMember.PayMode.HOURLY: Decimal(staff.pay_rate) * row["hours"],
            StaffMember.PayMode.MONTHLY: Decimal(0),
        }[mode]
        if row["status"] == "absent":
            due = Decimal(0)
        paid = StaffPayment.objects.filter(staff=staff, date=day)
        if reservation is not None:
            paid = paid.filter(reservation=reservation)
        already = int(paid.aggregate(total=Sum("amount"))["total"] or 0)
        rows.append(
            {
                "staff": str(staff.pk),
                "name": staff.full_name,
                "position": staff.position,
                "pay_mode": staff.pay_mode,
                "pay_rate": staff.pay_rate,
                "mobile_money": staff.mobile_money,
                "status": row["status"],
                "hours": float(row["hours"].quantize(Decimal("0.01"))),
                "reservations": sorted(row["reservations"].values()),
                "salaried": mode == StaffMember.PayMode.MONTHLY,
                "suggested": max(0, int(due.quantize(Decimal(1), ROUND_HALF_UP)) - already),
                "already_paid": already,
            }
        )
    rows.sort(key=lambda r: (r["salaried"], r["name"]))
    return rows


@transaction.atomic
def pay_now(
    day: date,
    lines: list[dict[str, Any]],
    *,
    method: str,
    user: User,
    reservation: Any = None,
    request: Any = None,
) -> list[StaffPayment]:
    """Pays several people at once, one expense each (« Salaires et journaliers »)."""
    from finance.defaults import ensure_expense_categories
    from finance.models import Expense, ExpenseCategory

    prepared = []
    for line in lines:
        try:
            items = payroll.clean_items(line.get("items") or [])
        except ValueError as exc:
            raise BusinessError("invalid", str(exc)) from exc
        raw = line.get("base")
        base = int(raw if raw is not None else line.get("amount") or 0)
        if base < 0:
            raise BusinessError("invalid", "Les montants sont positifs.")
        # Paid on the spot: no contributions withheld (they come with the month for the declared).
        slip = payroll.compute(base, items, declared=False, settings=payroll.Settings())
        if slip.net > 0:
            prepared.append({**line, "base": base, "items": items, "amount": slip.net})
    lines = prepared
    if not lines:
        raise BusinessError("invalid", "Indiquez au moins un montant à payer.")
    ensure_expense_categories()
    category = ExpenseCategory.objects.get(name="Salaires et journaliers")
    where = f" — {reservation.number}" if reservation is not None else ""
    payments = []
    for line in lines:
        staff = line["staff"]
        amount = int(line["amount"])
        expense = Expense.objects.create(
            label=f"Journée du {day:%d/%m/%Y} — {staff.full_name}{where}",
            amount=amount,
            date=day,
            category=category,
            reservation=reservation,
            supplier=staff.full_name,
            method=method,
            is_paid=True,
            created_by=user,
        )
        payments.append(
            StaffPayment.objects.create(
                staff=staff,
                reservation=reservation,
                date=day,
                base=int(line["base"]),
                items=line["items"],
                hours=Decimal(str(line.get("hours") or 0)).quantize(Decimal("0.01")),
                amount=amount,
                method=method,
                note=str(line.get("note") or "")[:160],
                expense=expense,
                created_by=user,
            )
        )
    audit.record(
        "staff.paid_on_the_spot",
        require_current_organization(),
        request=request,
        changes={
            "date": str(day),
            "count": len(payments),
            "total": sum(p.amount for p in payments),
        },
    )
    from notifications import flow

    for payment in payments:  # the person learns it is paid (never the amount in the push)
        flow.to_person(
            payment.staff.user_id,
            title="Paiement de votre journée",
            body=f"Journée du {day:%d/%m/%Y} enregistrée comme payée.",
            url="/mes-missions",
            kind="pay",
            tag=f"pay-{payment.pk}",
        )
    return payments


# --- Badges: employee number and the signed verification link ------------------------------------

BADGE_SALT = "wedivo.staff.badge"


def ensure_employee_number(staff: StaffMember) -> str:
    """« ME-2026-001 »: agency initials, year of arrival, order of arrival. Kept once given."""
    if staff.employee_number:
        return staff.employee_number
    from documents import services as branding_services

    branding = branding_services.get_branding()
    import unicodedata

    raw = branding_services.monogram(branding.trade_name or branding.organization.name)
    prefix = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode() or "WD"
    year = timezone.localtime(staff.created_at).year
    taken = set(
        StaffMember.objects.filter(employee_number__startswith=f"{prefix}-{year}-").values_list(
            "employee_number", flat=True
        )
    )
    number = 1
    while f"{prefix}-{year}-{number:03d}" in taken:
        number += 1
    staff.employee_number = f"{prefix}-{year}-{number:03d}"
    staff.save(update_fields=["employee_number", "updated_at"])
    return staff.employee_number


def _badge_mac(raw: bytes) -> bytes:
    import hashlib
    import hmac

    from django.conf import settings

    key = hashlib.sha256(f"{BADGE_SALT}:{settings.SECRET_KEY}".encode()).digest()
    return hmac.new(key, raw, hashlib.sha256).digest()[:10]


def _b64(raw: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def badge_token(staff: StaffMember) -> str:
    """36 characters (a light QR, like the reference): the staff id (16 bytes) and an HMAC
    truncated to 10 bytes, base64url. The id is unique across agencies: the check page finds
    the agency from it."""
    raw = staff.pk.bytes
    return _b64(raw) + _b64(_badge_mac(raw))


def badge_from_token(token: str) -> StaffMember | None:
    """The staff member of a badge, or None if the signature is wrong (forged or altered)."""
    import base64
    import hmac
    import uuid

    from core.tenant import bypass_tenant

    if len(token) != 36:
        return None
    try:
        raw = base64.urlsafe_b64decode(token[:22] + "==")
        mac = base64.urlsafe_b64decode(token[22:] + "==")
    except ValueError:
        return None
    if len(raw) != 16 or not hmac.compare_digest(mac, _badge_mac(raw)):
        return None
    if _b64(raw) + _b64(mac) != token:  # canonical form only
        return None
    staff_id = uuid.UUID(bytes=raw)
    with bypass_tenant():
        found: StaffMember | None = (
            StaffMember.all_tenants.select_related("organization").filter(pk=staff_id).first()
        )
    return found


def badge_url(staff: StaffMember) -> str:
    """What the QR opens: the public check page « Badge valide » (never any private data)."""
    from django.conf import settings

    return f"{settings.FRONTEND_URL.rstrip('/')}/b/{badge_token(staff)}"


# --- Deleting a person (feedback 13/11/2026) ------------------------------------------------------


@dataclass(frozen=True)
class Deletion:
    permanent: bool  # nothing to keep: the record is gone
    removed_assignments: int  # upcoming missions taken off the planning
    access_closed: bool  # their Wedivo account no longer opens this space


@transaction.atomic
def delete_staff(staff: StaffMember) -> Deletion:
    """Delete a person. Without any history the record goes; otherwise it leaves every list but
    the missions done, check-ins, pay and payments keep their name. Upcoming missions nobody has
    checked in are removed (with their tasks); their account loses this space."""
    from accounts.models import Membership

    staff = StaffMember.objects.select_for_update().get(pk=staff.pk)
    now = timezone.now()
    upcoming = Assignment.objects.filter(staff=staff, start__gt=now, attendance__isnull=True)
    reservations = list(upcoming.values_list("reservation_id", flat=True))
    removed = upcoming.count()
    StaffTask.objects.filter(
        staff=staff, reservation_id__in=reservations, status=StaffTask.Status.TODO
    ).delete()
    upcoming.delete()

    access_closed = False
    if staff.user_id is not None:
        access_closed = bool(
            Membership.objects.filter(
                user_id=staff.user_id,
                organization=require_current_organization(),
                is_active=True,
            )
            .exclude(role=Membership.Role.OWNER)
            .update(is_active=False)
        )

    has_history = (
        Assignment.objects.filter(staff=staff).exists()
        or Attendance.objects.filter(staff=staff).exists()
        or PayLine.objects.filter(staff=staff).exists()
        or StaffPayment.objects.filter(staff=staff).exists()
    )
    if not has_history:
        StaffTask.objects.filter(staff=staff).delete()
        if staff.photo:
            staff.photo.delete(save=False)
        staff.delete()
        return Deletion(permanent=True, removed_assignments=removed, access_closed=access_closed)
    staff.is_deleted, staff.is_active, staff.deleted_at = True, False, now
    staff.save(update_fields=["is_deleted", "is_active", "deleted_at", "updated_at"])
    return Deletion(permanent=False, removed_assignments=removed, access_closed=access_closed)


# --- « Mon espace »: the personal overview of a field account (feedback 13/11/2026) --------------

WEEKS_OF_HOURS = 8


def mission_state(assignment: Assignment, now: datetime) -> str:
    """`done` (over or checked out), `in_progress` (started or checked in) or `upcoming`."""
    attendance = getattr(assignment, "attendance", None)
    if (attendance is not None and attendance.check_out) or assignment.end < now:
        return "done"
    if (attendance is not None and attendance.check_in) or assignment.start <= now:
        return "in_progress"
    return "upcoming"


def overview(staff: StaffMember, *, with_team: bool) -> dict[str, Any]:
    """What a person needs on opening the app: the figures of their work (missions, hours,
    punctuality, tasks), hours per week over 8 weeks and, for a team lead, today's team.
    Never an amount: pay stays with the owner and the accountant."""
    tz = org_tz(require_current_organization())
    now = timezone.now()
    day = timezone.localdate(now, tz)
    week_start = day - timedelta(days=day.weekday())
    month_start = day.replace(day=1)

    def at(d: date) -> datetime:
        return datetime.combine(d, datetime.min.time(), tzinfo=tz)

    live = Assignment.objects.filter(staff=staff).exclude(reservation__status="cancelled")
    attendances = Attendance.objects.filter(staff=staff)
    recent = attendances.filter(date__gte=day - timedelta(days=90), date__lte=day)
    hours_month = attendances.filter(date__gte=month_start, date__lte=day).aggregate(
        total=Sum("hours")
    )["total"] or Decimal(0)
    statuses = {key: recent.filter(status=key).count() for key in ("present", "late", "absent")}
    counted = sum(statuses.values())

    first_week = week_start - timedelta(weeks=WEEKS_OF_HOURS - 1)
    per_week: dict[date, Decimal] = {
        first_week + timedelta(weeks=i): Decimal(0) for i in range(WEEKS_OF_HOURS)
    }
    for row in attendances.filter(date__gte=first_week, date__lte=day).values("date", "hours"):
        monday = row["date"] - timedelta(days=row["date"].weekday())
        if monday in per_week:
            per_week[monday] += row["hours"] or 0

    tasks = StaffTask.objects.filter(staff=staff).exclude(reservation__status="cancelled")
    next_mission = live.filter(end__gte=now).order_by("start").first()

    team: list[dict[str, Any]] = []
    if with_team:
        tomorrow = at(day + timedelta(days=1))
        mine_today = live.filter(start__lt=tomorrow, end__gte=at(day))
        for other in (
            Assignment.objects.filter(
                reservation_id__in=mine_today.values("reservation_id"),
                start__lt=tomorrow,
                end__gte=at(day),
            )
            .exclude(staff=staff)
            .select_related("staff", "reservation", "attendance")
            .order_by("start", "staff__full_name")
        ):
            attendance = getattr(other, "attendance", None)
            team.append(
                {
                    "assignment": str(other.pk),
                    "name": other.staff.full_name,
                    "role": other.role or other.staff.position,
                    "reservation": other.reservation.number,
                    "start": other.start,
                    "attendance": attendance.status if attendance else None,
                    "checked_in": bool(attendance and attendance.check_in),
                }
            )

    return {
        "missions_week": live.filter(
            start__lt=at(week_start + timedelta(days=7)), end__gte=at(week_start)
        ).count(),
        "missions_month": live.filter(
            start__gte=at(month_start), start__lt=at(day + timedelta(days=1))
        ).count(),
        "hours_month": float(hours_month),
        "punctuality": round(statuses["present"] * 100 / counted) if counted else None,
        "attendance": statuses,
        "tasks": {key: tasks.filter(status=key).count() for key in ("todo", "done", "validated")},
        "hours_by_week": [
            {"week": monday.isoformat(), "hours": float(hours)}
            for monday, hours in per_week.items()
        ],
        "next_mission": str(next_mission.pk) if next_mission else None,
        "team": team,
    }
