"""Weddings and tasks (CLAUDE.md §7.6, complement §11)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from accounts.models import User
from core.exceptions import BusinessError

from .defaults import ensure_standard_tasks
from .models import Task, TaskTemplateItem, Wedding

# A standard task whose date has already passed is due three days from now (complement §11).
LATE_STANDARD_TASK_DAYS = 3


def standard_due_date(wedding_date: date | None, days_before: int, today: date) -> date | None:
    if wedding_date is None:
        return None
    due = wedding_date - timedelta(days=days_before)
    return due if due >= today else today + timedelta(days=LATE_STANDARD_TASK_DAYS)


@transaction.atomic
def add_standard_tasks(wedding: Wedding, *, user: User | None) -> list[Task]:
    """Append the agency's standard list to a wedding (dates counted back from the wedding)."""
    ensure_standard_tasks()
    today = timezone.localdate()
    tasks = [
        Task(
            organization_id=wedding.organization_id,  # bulk_create skips save()
            wedding=wedding,
            title=item.title,
            due_date=standard_due_date(wedding.date, item.days_before, today),
            created_by=user,
        )
        for item in TaskTemplateItem.objects.all()
    ]
    return Task.objects.bulk_create(tasks)


@transaction.atomic
def create_wedding(data: dict[str, Any], *, standard_tasks: bool, user: User) -> Wedding:
    wedding: Wedding = Wedding.objects.create(**data, created_by=user)
    if standard_tasks:
        add_standard_tasks(wedding, user=user)
    return wedding


def set_task_done(task: Task, done: bool) -> Task:
    task.status = Task.Status.DONE if done else Task.Status.TODO
    task.done_at = timezone.now() if done else None
    task.save(update_fields=["status", "done_at", "updated_at"])
    return task


def delete_wedding(wedding: Wedding) -> None:
    """A wedding tied to a contract stays: its money history depends on it."""
    if wedding.contract_id:
        raise BusinessError(
            "wedding_has_contract",
            "Ce mariage est lié à un contrat : passez-le plutôt au statut « Annulé ».",
        )
    wedding.delete()


ALERT_DAYS_BEFORE = 2


def send_due_task_alerts(today: date) -> int:
    """Email each assignee about their open tasks due in two days (once per due date)."""
    from django.conf import settings
    from django.core.mail import send_mail

    from core.tenant import require_current_organization

    target = today + timedelta(days=ALERT_DAYS_BEFORE)
    tasks = list(
        Task.objects.filter(
            status=Task.Status.TODO,
            due_date=target,
            assignee__isnull=False,
            assignee__is_active=True,
        )
        .exclude(alert_sent_for=target)
        .select_related("assignee", "wedding")
    )
    organization = require_current_organization()
    by_person: dict[User, list[Task]] = {}
    for task in tasks:
        by_person.setdefault(task.assignee, []).append(task)
    for person, items in by_person.items():
        lines = "\n".join(f"- {task.title} ({task.wedding.title})" for task in items)
        send_mail(
            subject=(
                f"{len(items)} tâche{'s' if len(items) > 1 else ''} à faire dans 2 jours"
                f" — {organization.name}"
            ),
            message=(
                f"Bonjour {person.first_name},\n\nCes tâches arrivent à échéance le "
                f"{target.strftime('%d/%m/%Y')} :\n{lines}\n\n"
                f"Retrouvez-les dans Wedivo : {settings.FRONTEND_URL}/mariages\n\n"
                f"{organization.name}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[person.email],
        )
    Task.objects.filter(pk__in=[task.pk for task in tasks]).update(alert_sent_for=target)
    return len(tasks)
