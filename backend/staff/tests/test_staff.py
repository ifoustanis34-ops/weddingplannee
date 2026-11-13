"""Staff (reservations-stock.md §7, §12): assignments and conflicts, check-in, pay, missions."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from typing import Any

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Membership, User
from core.exceptions import BusinessError
from core.tenant import tenant_context
from crm.models import Client
from finance.defaults import ensure_expense_categories
from finance.models import Expense
from organizations.models import Organization
from reservations import services as reservation_services
from reservations.models import Reservation
from staff import services
from staff.models import Attendance, PayLine, PayPeriod, StaffMember
from stock import services as stock_services
from stock.defaults import ensure_item_categories
from stock.models import ItemCategory

Role = Membership.Role


@pytest.fixture(autouse=True)
def _defaults(org_a: Organization, org_b: Organization) -> None:
    for organization in (org_a, org_b):
        with tenant_context(organization):
            ensure_item_categories()
            ensure_expense_categories()


def at(days: int, hour: int = 10) -> datetime:
    return timezone.make_aware(
        datetime.combine(timezone.localdate() + timedelta(days=days), time(hour))
    )


def reservation(org: Organization, user: User, start: int = 5) -> Reservation:
    with tenant_context(org):
        chairs = stock_services.create_item(
            {
                "name": f"Chaise {start}",
                "category": ItemCategory.objects.get(name="Mobilier"),
                "rent_price": 1000,
                "initial_quantity": 100,
            },
            user=user,
        )
        created = reservation_services.create_reservation(
            {
                "client": Client.objects.create(name=f"Client {start}"),
                "title": "Mariage Awa & Koffi",
                "venue": "Salle Bellevue",
                "address": "Cocody, Abidjan",
                "delivery_at": at(start - 1, 9),
                "setup_at": at(start - 1, 14),
                "event_start": at(start, 15),
                "event_end": at(start, 23),
                "pickup_at": at(start + 1, 10),
                "return_at": at(start + 1, 15),
            },
            [reservation_services.LineInput(kind="rental", item=chairs, quantity=50)],
            user=user,
        )
        reservation_services.confirm(created, user=user)
        created.refresh_from_db()
    return created


def person(
    org: Organization, name: str, mode: str = "daily", rate: int = 8000, **extra: Any
) -> StaffMember:
    with tenant_context(org):
        member: StaffMember = StaffMember.objects.create(
            full_name=name,
            position=extra.pop("position", "Installateur"),
            pay_mode=mode,
            pay_rate=rate,
            **extra,
        )
    return member


def test_steps_windows_and_conflicts(org_a: Organization, owner_a: User) -> None:
    first = reservation(org_a, owner_a, 5)
    second = reservation(org_a, owner_a, 5)
    brice = person(org_a, "Brice Ndzana")
    with tenant_context(org_a):
        delivery, found = services.assign(first, brice, step="delivery", role="", user=owner_a)
        assert (delivery.start, delivery.end) == (at(4, 9), at(4, 12))
        assert delivery.role == "Installateur" and found == []
        event, _ = services.assign(first, brice, step="event", role="Manutention", user=owner_a)
        assert (event.start, event.end) == (at(5, 15), at(5, 23))
        # Same time on another reservation: allowed, with the alert of §7.
        _, clash = services.assign(second, brice, step="event", role="", user=owner_a)
        assert [c.kind for c in clash] == ["overlap"]
        assert first.number in clash[0].message
        with pytest.raises(BusinessError):
            services.assign(first, brice, step="event", role="", user=owner_a)  # twice


def test_absence_is_a_conflict_and_assignments_follow_a_move(
    org_a: Organization, owner_a: User
) -> None:
    booked = reservation(org_a, owner_a, 5)
    carine = person(org_a, "Carine Essomba")
    with tenant_context(org_a):
        assignment, _ = services.assign(booked, carine, step="all", role="", user=owner_a)
        services.mark_absent(assignment, user=owner_a, note="Malade")
        other = reservation(org_a, owner_a, 4)
        _, found = services.assign(other, carine, step="event", role="", user=owner_a)
        assert "absent" in [c.kind for c in found]

        reservation_services.move(booked, days=2, user=owner_a)
        assignment.refresh_from_db()
        assert assignment.start == at(6, 9)  # delivery → return, two days later


def test_check_in_late_hours_and_rights(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
) -> None:
    booked = reservation(org_a, owner_a, 0)
    lead_user = make_member(org_a, Role.TEAM_LEAD)
    staff_user = make_member(org_a, Role.STAFF)
    didier = person(
        org_a, "Didier Kra", "monthly", 200_000, user=lead_user, position="Chef d’équipe"
    )
    linda = person(org_a, "Linda Abena", "daily", 7000, user=staff_user, position="Serveuse")
    patrick = person(org_a, "Patrick Nkolo")
    with tenant_context(org_a):
        lead, _ = services.assign(booked, didier, step="event", role="", user=owner_a)
        mine, _ = services.assign(booked, linda, step="event", role="", user=owner_a)
        stranger_res = reservation(org_a, owner_a, 10)
        elsewhere, _ = services.assign(stranger_res, patrick, step="event", role="", user=owner_a)

        attendance = services.check_in(mine, user=owner_a, at=at(0, 15) + timedelta(minutes=40))
        assert attendance.status == Attendance.Status.LATE
        attendance = services.check_out(mine, user=owner_a, at=at(0, 23) + timedelta(minutes=10))
        assert attendance.hours == 7.5

    team_lead = client_for(lead_user, org_a)
    assert team_lead.post(reverse("assignment-check-in", args=[lead.pk])).status_code == 200
    assert team_lead.post(reverse("assignment-absent", args=[mine.pk])).status_code == 200
    assert team_lead.post(reverse("assignment-check-in", args=[elsewhere.pk])).status_code == 403

    staff = client_for(staff_user, org_a)
    assert staff.post(reverse("assignment-check-in", args=[mine.pk])).status_code == 200
    assert staff.post(reverse("assignment-check-in", args=[lead.pk])).status_code == 403
    assert staff.post(reverse("assignment-absent", args=[mine.pk])).status_code == 403
    assert staff.get(reverse("staff-list")).status_code == 403  # the directory is not theirs

    missions = staff.get(reverse("my-missions")).json()
    mission = missions["missions"][0]
    assert mission["reservation_number"] == booked.number
    assert mission["maps_url"].startswith("https://www.google.com/maps/search/?api=1&query=Cocody")
    assert mission["equipment"] == [{"label": "Chaise 0", "quantity": 50}]  # never a price
    assert mission["team"] == []  # only the team lead sees the team
    lead_view = team_lead.get(reverse("my-missions")).json()["missions"][0]
    assert {member["name"] for member in lead_view["team"]} == {"Linda Abena"}


def test_pay_from_attendance_bonuses_validation_and_payment(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
) -> None:
    first = reservation(org_a, owner_a, -20)
    second = reservation(org_a, owner_a, -10)
    person(org_a, "Awa Sangaré", "monthly", 250_000)
    brice = person(org_a, "Brice Ndzana", "daily", 8000)
    mireille = person(org_a, "Mireille Fotso", "mission", 40_000)
    serge = person(org_a, "Serge Atangana", "hourly", 1500)
    with tenant_context(org_a):
        for booked in (first, second):
            for member in (brice, mireille, serge):
                assignment, _ = services.assign(booked, member, step="event", role="", user=owner_a)
                services.check_in(assignment, user=owner_a, at=assignment.start)
                services.check_out(
                    assignment, user=owner_a, at=assignment.start + timedelta(hours=8)
                )
        today = timezone.localdate()
        period = services.create_period(today - timedelta(days=30), today, user=owner_a)
        lines = {line.staff.full_name: line for line in period.lines.select_related("staff")}
        assert lines["Brice Ndzana"].base == 16_000  # 2 days × 8 000
        assert lines["Mireille Fotso"].base == 40_000 * 2  # 2 missions
        assert lines["Serge Atangana"].base == 24_000  # 16 h × 1 500
        assert lines["Awa Sangaré"].base == 258_333  # 31 days ÷ 30 of a month
        assert services._months(date(2026, 10, 1), date(2026, 10, 31)) == 1  # whole month

        line = services.update_line(lines["Brice Ndzana"], bonuses=5000, advances=3000)
        assert line.total == 18_000
        with pytest.raises(BusinessError):
            services.pay_line(line, method="cash", paid_at=today, user=owner_a)  # not validated

    accountant = client_for(make_member(org_a, Role.ACCOUNTANT), org_a)
    assert accountant.post(reverse("pay-period-validate", args=[period.pk])).status_code == 403
    owner = client_for(owner_a, org_a)
    assert (
        owner.post(reverse("pay-period-validate", args=[period.pk])).json()["status"] == "validated"
    )
    assert (
        accountant.patch(reverse("pay-line-detail", args=[line.pk]), {"bonuses": 1}).status_code
        == 400
    )

    with tenant_context(org_a):
        ids = list(PayLine.objects.filter(period=period, total__gt=0).values_list("pk", flat=True))
    for pk in ids:
        paid = accountant.post(reverse("pay-line-pay", args=[pk]), {"method": "orange_money"})
        assert paid.status_code == 200
    with tenant_context(org_a):
        assert PayPeriod.objects.get(pk=period.pk).status == PayPeriod.Status.PAID
        salaries = Expense.objects.filter(category__name="Salaires et journaliers")
        assert salaries.count() == len(ids)
        assert sum(e.amount for e in salaries) == sum(
            PayLine.objects.filter(period=period).values_list("total", flat=True)
        )
    pdf = accountant.get(reverse("pay-line-statement", args=[ids[0]]))
    assert pdf.content.startswith(b"%PDF")


def test_money_hidden_from_the_planner_and_isolation(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    org_b: Organization,
    owner_a: User,
    owner_b: User,
) -> None:
    joel = person(org_a, "Joël Mbarga", "monthly", 150_000, position="Magasinier")
    planner = client_for(make_member(org_a, Role.PLANNER), org_a)
    row = next(
        r for r in planner.get(reverse("staff-list")).json() if r["full_name"] == "Joël Mbarga"
    )
    assert row["pay_rate"] is None and row["today"]["status"] == "free"
    planner.patch(reverse("staff-detail", args=[joel.pk]), {"pay_rate": 1}, format="json")
    with tenant_context(org_a):
        joel.refresh_from_db()
        assert joel.pay_rate == 150_000  # the planner never sets a salary
    assert planner.get(reverse("pay-period-list")).status_code == 403
    assert planner.get(reverse("staff-stats")).json()["payroll_month"] is None

    other = client_for(owner_b, org_b)
    assert other.get(reverse("staff-detail", args=[joel.pk])).status_code == 404
    assert other.get(reverse("staff-list")).json() == []


def test_team_in_calendar_profitability_and_dashboard(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
) -> None:
    booked = reservation(org_a, owner_a, 0)
    staff_user = make_member(org_a, Role.STAFF)
    brice = person(org_a, "Brice Ndzana", user=staff_user)
    with tenant_context(org_a):
        assignment, _ = services.assign(booked, brice, step="all", role="", user=owner_a)
        services.check_in(assignment, user=owner_a, at=assignment.start + timedelta(minutes=30))
    owner = client_for(owner_a, org_a)
    day = timezone.localdate()
    items = owner.get(
        reverse("calendar"),
        {"from": (day - timedelta(1)).isoformat(), "to": (day + timedelta(2)).isoformat()},
    ).json()
    delivery = next(i for i in items if i["kind"] == "delivery")
    assert delivery["team"] == ["Brice Ndzana"]
    mine = owner.get(
        reverse("calendar"),
        {
            "from": day.isoformat(),
            "to": (day + timedelta(2)).isoformat(),
            "member": str(staff_user.pk),
        },
    ).json()
    assert {i["reservation"] for i in mine} == {str(booked.pk)}

    rows = owner.get(reverse("finance-profitability"), {"by": "event", "period": "month"}).json()
    row = next(r for r in rows["rows"] if r["number"] == booked.number)
    assert row["staff_costs"] == 8000  # one day of a day worker
    team = owner.get(reverse("dashboard-summary"), {"period": "today"}).json()["team_today"]
    assert team == [
        {"name": "Brice Ndzana", "total": 1, "done": 0, "status": "in_progress", "late": True}
    ]


def test_photo_and_badges(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    org_b: Organization,
    owner_a: User,
    owner_b: User,
) -> None:
    import io

    from PIL import Image

    brice = person(org_a, "Brice Ndzana")
    person(org_a, "Linda Abena", position="Serveuse")
    owner = client_for(owner_a, org_a)
    picture = io.BytesIO()
    Image.new("RGB", (300, 400), "#5126c2").save(picture, "JPEG")
    picture.seek(0)
    picture.name = "brice.jpg"
    uploaded = owner.post(
        reverse("staff-photo", args=[brice.pk]), {"file": picture}, format="multipart"
    )
    assert uploaded.status_code == 200 and "/api/v1/files/" in uploaded.json()["photo_url"]

    every = owner.get(reverse("staff-badges"))
    assert every.status_code == 200 and every.content.startswith(b"%PDF")
    one = owner.get(reverse("staff-badges"), {"ids": str(brice.pk)})
    assert one.content.startswith(b"%PDF") and len(one.content) < len(every.content) * 2

    storekeeper = client_for(make_member(org_a, Role.STOREKEEPER), org_a)
    assert storekeeper.get(reverse("staff-badges")).status_code == 403
    # Another agency never prints these people: the ids are not found in its space.
    assert (
        client_for(owner_b, org_b).get(reverse("staff-badges"), {"ids": str(brice.pk)}).status_code
        == 400
    )


def test_tasks_listed_by_person_and_event(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
) -> None:
    later = reservation(org_a, owner_a, 9)
    sooner = reservation(org_a, owner_a, 3)
    brice = person(org_a, "Brice Ndzana")
    awa = person(org_a, "Awa Sangaré", position="Décoratrice")
    owner = client_for(owner_a, org_a)
    url = reverse("staff-task-list")
    for staff, booked, title in (
        (brice, later, "Monter le chapiteau"),
        (brice, sooner, "Monter les tables"),
        (awa, sooner, "Composer l’arche"),
    ):
        created = owner.post(
            url, {"staff": str(staff.pk), "reservation": str(booked.pk), "title": title}
        )
        assert created.status_code == 201, created.json()
    assert (
        owner.post(
            url, {"staff": str(brice.pk), "reservation": str(later.pk), "title": "  "}
        ).status_code
        == 400
    )

    rows = owner.get(url).json()
    # By person (alphabetical), then the coming events first.
    assert [(r["staff_name"], r["title"]) for r in rows] == [
        ("Awa Sangaré", "Composer l’arche"),
        ("Brice Ndzana", "Monter les tables"),
        ("Brice Ndzana", "Monter le chapiteau"),
    ]
    assert rows[0]["reservation_title"] == "Mariage Awa & Koffi" and rows[0]["event_start"]
    owner.patch(reverse("staff-task-detail", args=[rows[0]["id"]]), {"status": "done"})
    assert [r["title"] for r in owner.get(url, {"status": "todo"}).json()] == [
        "Monter les tables",
        "Monter le chapiteau",
    ]

    assistant = client_for(make_member(org_a, Role.ASSISTANT), org_a)
    assert len(assistant.get(url).json()) == 3
    assert (
        assistant.post(
            url, {"staff": str(brice.pk), "reservation": str(later.pk), "title": "X"}
        ).status_code
        == 403
    )


def test_a_task_is_done_by_the_person_then_validated_or_sent_back(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
) -> None:
    booked = reservation(org_a, owner_a, 2)
    staff_user = make_member(org_a, Role.STAFF)
    brice = person(org_a, "Brice Ndzana", user=staff_user)
    owner = client_for(owner_a, org_a)
    task = owner.post(
        reverse("staff-task-list"),
        {"staff": str(brice.pk), "reservation": str(booked.pk), "title": "Monter l’arche"},
    ).json()
    mine = client_for(staff_user, org_a)
    done = mine.patch(
        reverse("staff-task-detail", args=[task["id"]]),
        {"status": "done", "comment": "Arche montée, photo jointe"},
        format="json",
    ).json()
    assert (done["status"], done["done_by_name"], done["comment"]) == (
        "done",
        staff_user.full_name,
        "Arche montée, photo jointe",
    )
    # Only the owner or the planner validates.
    assert mine.post(reverse("staff-task-validate", args=[task["id"]])).status_code == 403
    sent_back = owner.post(
        reverse("staff-task-reject", args=[task["id"]]), {"reason": "Il manque les fleurs"}
    ).json()
    assert (sent_back["status"], sent_back["rejection_reason"]) == ("todo", "Il manque les fleurs")
    assert owner.post(reverse("staff-task-validate", args=[task["id"]])).status_code == 400

    mine.patch(reverse("staff-task-detail", args=[task["id"]]), {"status": "done"}, format="json")
    validated = owner.post(reverse("staff-task-validate", args=[task["id"]])).json()
    assert (validated["status"], validated["validated_by_name"]) == (
        "validated",
        owner_a.full_name,
    )
    assert validated["rejection_reason"] == ""
    locked = mine.patch(
        reverse("staff-task-detail", args=[task["id"]]), {"status": "todo"}, format="json"
    )
    assert locked.status_code == 400  # validated: the person cannot undo it
    rows = owner.get(reverse("staff-task-list"), {"status": "validated"}).json()
    assert [r["title"] for r in rows] == ["Monter l’arche"]


def test_pay_the_day_workers_on_the_spot_then_the_period_deducts_it(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
) -> None:
    booked = reservation(org_a, owner_a, -1)
    brice = person(org_a, "Brice Ndzana", "daily", 8000)
    carine = person(org_a, "Carine Essomba", "daily", 10_000)
    awa = person(org_a, "Awa Sangaré", "monthly", 250_000)
    with tenant_context(org_a):
        for member in (brice, carine, awa):
            assignment, _ = services.assign(booked, member, step="event", role="", user=owner_a)
            services.check_in(assignment, user=owner_a, at=assignment.start)
            services.check_out(assignment, user=owner_a, at=assignment.start + timedelta(hours=8))
    owner = client_for(owner_a, org_a)
    day = (timezone.localdate() - timedelta(days=1)).isoformat()
    sheet = owner.get(reverse("pay-day"), {"date": day}).json()
    assert [r["number"] for r in sheet["reservations"]] == [booked.number]
    rows = {r["name"]: r for r in sheet["rows"]}
    assert rows["Brice Ndzana"]["suggested"] == 8000 and rows["Brice Ndzana"]["status"] == "present"
    assert rows["Awa Sangaré"]["salaried"] and rows["Awa Sangaré"]["suggested"] == 0

    paid = owner.post(
        reverse("staff-payment-list"),
        {
            "date": day,
            "reservation": str(booked.pk),
            "method": "mtn_momo",
            "lines": [
                {"staff": str(brice.pk), "amount": 8000},
                {"staff": str(carine.pk), "amount": 10_000, "note": "Prime incluse"},
                {"staff": str(awa.pk), "amount": 0},
            ],
        },
        format="json",
    )
    assert paid.status_code == 201 and len(paid.json()) == 2
    again = {r["name"]: r for r in owner.get(reverse("pay-day"), {"date": day}).json()["rows"]}
    assert (again["Brice Ndzana"]["suggested"], again["Brice Ndzana"]["already_paid"]) == (0, 8000)
    with tenant_context(org_a):
        from finance.models import Expense

        assert Expense.objects.filter(category__name="Salaires et journaliers").count() == 2
        period = services.create_period(
            timezone.localdate() - timedelta(days=3), timezone.localdate(), user=owner_a
        )
        line = period.lines.get(staff=brice)
        assert (line.base, line.already_paid, line.total) == (8000, 8000, 0)  # never twice

    planner = client_for(make_member(org_a, Role.PLANNER), org_a)
    assert planner.get(reverse("pay-day"), {"date": day}).status_code == 403


@pytest.mark.parametrize("design", ["carte", "classique", "portrait", "elegant", "minimal"])
def test_badges_in_every_design(
    client_for: Callable[..., APIClient], org_a: Organization, owner_a: User, design: str
) -> None:
    person(org_a, "Brice Ndzana")
    owner = client_for(owner_a, org_a)
    pdf = owner.get(reverse("staff-badges"), {"design": design})
    assert pdf.content.startswith(b"%PDF")
    png = owner.get(reverse("staff-badge-preview"), {"design": design})
    assert png["Content-Type"] == "image/png" and png.content.startswith(b"\x89PNG")
    assert owner.get(reverse("staff-badges"), {"design": "nope"}).status_code == 400


def test_employee_card_number_and_public_check(
    client_for: Callable[..., APIClient], org_a: Organization, owner_a: User
) -> None:
    owner = client_for(owner_a, org_a)
    created = owner.post(
        reverse("staff-list"),
        {"full_name": "Stanis Ifou", "position": "Chef d’équipe", "department": "Logistique"},
        format="json",
    ).json()
    number = created["employee_number"]
    assert re.fullmatch(r"[A-Z]{1,3}-\d{4}-001", number), number  # ASCII, no accent
    with tenant_context(org_a):
        stanis = StaffMember.objects.get(pk=created["id"])
        token = services.badge_token(stanis)
        assert services.badge_url(stanis).endswith(f"/b/{token}")
        assert len(token) < 80  # a light QR

    public = APIClient()  # anyone who scans the badge
    body = public.get(reverse("public-badge", args=[token])).json()
    assert (body["valid"], body["name"], body["number"], body["department"]) == (
        True,
        "Stanis Ifou",
        number,
        "Logistique",
    )
    assert "phone" not in body and "pay_rate" not in body
    assert public.get(reverse("public-badge", args=[token[:-2] + "xx"])).status_code == 404

    owner.patch(reverse("staff-detail", args=[created["id"]]), {"is_active": False}, format="json")
    assert public.get(reverse("public-badge", args=[token])).json()["valid"] is False
