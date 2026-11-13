"""Weddings, tasks and calendar (CLAUDE.md §7.6, complement §11)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta

import pytest
from django.db import connection
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Membership, User
from core.tenant import tenant_context
from events.defaults import STANDARD_TASKS
from events.models import Task, Wedding
from events.services import standard_due_date
from organizations.models import Organization

TODAY = date.today()


@pytest.fixture
def client(client_for: Callable[..., APIClient], owner_a: User, org_a: Organization) -> APIClient:
    return client_for(owner_a, org_a)


def create_wedding(client: APIClient, **extra: object) -> dict[str, object]:
    response = client.post(
        reverse("wedding-list"),
        {
            "title": "Mariam & Idriss",
            "date": (TODAY + timedelta(days=200)).isoformat(),
            "venue": "Sofitel Hôtel Ivoire, Cocody",
            "guest_count": 320,
            **extra,
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    body: dict[str, object] = response.json()
    return body


def test_standard_due_dates_count_back_and_late_ones_move_to_three_days() -> None:
    wedding_day = TODAY + timedelta(days=100)
    assert standard_due_date(wedding_day, 30, TODAY) == wedding_day - timedelta(days=30)
    assert standard_due_date(wedding_day, 180, TODAY) == TODAY + timedelta(days=3)
    assert standard_due_date(None, 30, TODAY) is None


def test_new_wedding_with_the_twelve_standard_tasks(client: APIClient) -> None:
    wedding = create_wedding(client, standard_tasks=True)

    assert (wedding["tasks_total"], wedding["tasks_done"], wedding["progress"]) == (12, 0, 0)
    tasks = client.get(reverse("wedding-tasks", args=[wedding["id"]])).json()
    assert len(tasks) == len(STANDARD_TASKS) == 12
    assert {t["title"] for t in tasks} >= {"Réserver la salle", "Répétition de la cérémonie"}


def test_ticking_tasks_moves_the_progress(client: APIClient, owner_a: User) -> None:
    wedding = create_wedding(client)
    url = reverse("wedding-tasks", args=[wedding["id"]])
    first = client.post(url, {"title": "Valider le menu", "assignee": str(owner_a.pk)}).json()
    client.post(url, {"title": "Livraison décoration"})
    assert first["assignee_name"] == owner_a.full_name

    done = client.post(reverse("task-done", args=[first["id"]]), {"done": True}, format="json")
    assert done.json()["status"] == "done"
    detail = client.get(reverse("wedding-detail", args=[wedding["id"]])).json()
    assert (detail["tasks_done"], detail["tasks_total"], detail["progress"]) == (1, 2, 50)


def test_a_task_goes_to_a_member_of_the_space_only(
    client: APIClient, org_b: Organization, owner_b: User
) -> None:
    wedding = create_wedding(client)
    response = client.post(
        reverse("wedding-tasks", args=[wedding["id"]]),
        {"title": "Réserver le DJ", "assignee": str(owner_b.pk)},
    )
    assert response.status_code == 400


def test_the_accountant_reads_and_cannot_change(
    client: APIClient,
    client_for: Callable[..., APIClient],
    org_a: Organization,
    make_member: Callable[..., User],
) -> None:
    wedding = create_wedding(client)
    accountant = client_for(make_member(org_a, Membership.Role.ACCOUNTANT), org_a)
    assistant = client_for(make_member(org_a, Membership.Role.ASSISTANT), org_a)

    assert accountant.get(reverse("wedding-list")).status_code == 200
    assert accountant.post(reverse("wedding-list"), {"title": "X"}).status_code == 403
    assert (
        assistant.post(reverse("wedding-tasks", args=[wedding["id"]]), {"title": "Y"}).status_code
        == 201
    )


def test_a_wedding_with_a_contract_is_not_deleted(
    client: APIClient, org_a: Organization, owner_a: User
) -> None:
    from finance.tests.test_finance import make_contract

    plain = create_wedding(client)
    assert client.delete(reverse("wedding-detail", args=[plain["id"]])).status_code == 204
    contract = make_contract(org_a, owner_a)
    with tenant_context(org_a):
        tied = Wedding.objects.get(contract=contract)
    response = client.delete(reverse("wedding-detail", args=[tied.pk]))
    assert response.status_code == 400
    assert response.json()["code"] == "wedding_has_contract"


def test_calendar_shows_weddings_and_open_tasks_of_the_month(
    client: APIClient, owner_a: User
) -> None:
    day = TODAY + timedelta(days=10)
    wedding = create_wedding(client, date=day.isoformat())
    url = reverse("wedding-tasks", args=[wedding["id"]])
    open_task = client.post(url, {"title": "Plan de table", "due_date": day.isoformat()}).json()
    done_task = client.post(url, {"title": "Alliances", "due_date": day.isoformat()}).json()
    client.post(reverse("task-done", args=[done_task["id"]]), {"done": True}, format="json")

    items = client.get(
        reverse("calendar"), {"from": TODAY.isoformat(), "to": (TODAY + timedelta(30)).isoformat()}
    ).json()

    assert [(i["kind"], i["title"]) for i in items] == [
        ("event", "Mariam & Idriss"),
        ("task", "Plan de table"),
    ]
    mine = client.get(
        reverse("calendar"),
        {
            "from": TODAY.isoformat(),
            "to": (TODAY + timedelta(30)).isoformat(),
            "member": str(owner_a.pk),
        },
    ).json()
    assert [i["kind"] for i in mine] == ["event"]
    assert open_task["status"] == "todo"


def test_calendar_rejects_a_period_over_two_months(client: APIClient) -> None:
    response = client.get(
        reverse("calendar"), {"from": TODAY.isoformat(), "to": (TODAY + timedelta(90)).isoformat()}
    )
    assert response.status_code == 400


def test_weddings_and_tasks_stay_in_their_organization(
    client: APIClient,
    client_for: Callable[..., APIClient],
    org_a: Organization,
    org_b: Organization,
    owner_b: User,
) -> None:
    wedding = create_wedding(client, standard_tasks=True)
    task_id = client.get(reverse("wedding-tasks", args=[wedding["id"]])).json()[0]["id"]
    client_b = client_for(owner_b, org_b)

    assert client_b.get(reverse("wedding-list")).json() == []
    assert client_b.get(reverse("wedding-detail", args=[wedding["id"]])).status_code == 404
    assert client_b.patch(reverse("task-detail", args=[task_id]), {"title": "x"}).status_code == 404
    assert client_b.post(reverse("task-done", args=[task_id]), {"done": True}).status_code == 404
    assert client_b.delete(reverse("wedding-detail", args=[wedding["id"]])).status_code == 404
    with tenant_context(org_a):
        assert Task.objects.filter(pk=task_id, status="todo").exists()
        assert Wedding.objects.filter(pk=wedding["id"]).exists()


def test_new_tables_are_under_row_level_security(db: None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM pg_class WHERE relname IN"
            " ('events_task', 'events_tasktemplateitem', 'vendors_vendor',"
            " 'vendors_vendorassignment') AND relrowsecurity AND relforcerowsecurity"
        )
        assert cursor.fetchone() == (4,)


def test_assignees_get_one_email_two_days_before(
    client: APIClient, org_a: Organization, owner_a: User
) -> None:
    from django.core import mail

    from events.services import send_due_task_alerts

    wedding = create_wedding(client)
    url = reverse("wedding-tasks", args=[wedding["id"]])
    due = (TODAY + timedelta(days=2)).isoformat()
    client.post(
        url, {"title": "Briefing équipe jour J", "assignee": str(owner_a.pk), "due_date": due}
    )
    client.post(url, {"title": "Sans responsable", "due_date": due})

    with tenant_context(org_a):
        assert send_due_task_alerts(TODAY) == 1
        assert send_due_task_alerts(TODAY) == 0  # never twice for the same due date
    assert mail.outbox[-1].to == [owner_a.email]
    assert "Briefing équipe jour J" in mail.outbox[-1].body
