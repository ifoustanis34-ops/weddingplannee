"""Pay slips (feedback 24/11/2026): named lines, Cameroon contributions, monthly and daily slips."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Membership, User
from core.tenant import tenant_context
from organizations.models import Organization
from staff import payroll, services
from staff.tests.test_staff import _defaults, pdf_text, person, reservation  # noqa: F401

Role = Membership.Role
ON = payroll.Settings(enabled=True)


def test_without_contributions_net_is_gross_minus_deductions() -> None:
    items = payroll.clean_items(
        [
            {"label": "Prime de rendement", "amount": 20_000, "kind": "gain"},
            {"label": "Transport", "amount": 15_000, "kind": "gain", "taxable": False},
            {"label": "Avance du 10", "amount": 30_000, "kind": "deduction"},
            {"label": "", "amount": 5},  # ignored: no label
        ]
    )
    slip = payroll.compute(200_000, items, declared=True, settings=payroll.Settings())

    assert (slip.gross, slip.taxable, slip.employee, slip.net) == (235_000, 220_000, [], 205_000)


def test_cameroon_contributions_on_a_declared_salary() -> None:
    slip = payroll.compute(300_000, [], declared=True, settings=ON)
    lines = {c.code: c.amount for c in slip.employee}

    assert lines["cnps"] == 12_600  # 4,2 %
    # (300 000 × 70 % − 12 600) × 12 − 500 000 = 1 868 800 → 10 % → 186 880 / 12
    assert lines["irpp"] == 15_573
    assert lines["cac"] == 1_557
    assert lines["cfc"] == 3_000
    assert lines["rav"] == 3_250 and lines["tdl"] == 2_000
    assert slip.net == 300_000 - sum(lines.values())
    employer = {c.code: c.amount for c in slip.employer}
    assert employer["cnps_family"] == 21_000 and employer["fne"] == 3_000


def test_cnps_is_capped_and_the_irpp_scale_is_progressive() -> None:
    slip = payroll.compute(2_000_000, [], declared=True, settings=ON)
    assert next(c for c in slip.employee if c.code == "cnps").amount == 31_500  # 750 000 × 4,2 %
    assert payroll.irpp_yearly(2_000_000) == 200_000
    assert payroll.irpp_yearly(4_000_000) == 200_000 + 150_000 + 250_000
    # Not declared, or a small salary: nothing withheld / no IRPP.
    assert payroll.compute(300_000, [], declared=False, settings=ON).employee == []
    small = payroll.compute(50_000, [], declared=True, settings=ON)
    assert next(c for c in small.employee if c.code == "irpp").amount == 0


def test_named_lines_settings_and_monthly_slip(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
) -> None:
    awa = person(
        org_a,
        "Awa Sangaré",
        "monthly",
        300_000,
        kind="employee",
        declared=True,
        cnps_number="123-456-789",
        category="Catégorie 5",
    )
    owner = client_for(owner_a, org_a)
    accountant = client_for(make_member(org_a, Role.ACCOUNTANT), org_a)
    today = timezone.localdate()
    first = today.replace(day=1)
    period = owner.post(
        reverse("pay-period-list"),
        {
            "start": first.isoformat(),
            "end": (first + timedelta(days=40)).replace(day=1).isoformat(),
        },
        format="json",
    )
    # A whole calendar month: from the 1st to the last day.
    with tenant_context(org_a):
        from staff.models import PayLine, PayPeriod

        PayPeriod.objects.all().delete()
        import calendar

        last = first.replace(day=calendar.monthrange(first.year, first.month)[1])
        made = services.create_period(first, last, user=owner_a)
        line = PayLine.objects.get(period=made, staff=awa)
    assert period.status_code in (201, 400)

    edited = accountant.patch(
        reverse("pay-line-detail", args=[line.pk]),
        {
            "items": [
                {"label": "Heures supplémentaires", "amount": 25_000, "kind": "gain"},
                {
                    "label": "Indemnité de transport",
                    "amount": 15_000,
                    "kind": "gain",
                    "taxable": False,
                },
                {"label": "Avance", "amount": 50_000, "kind": "deduction"},
            ]
        },
        format="json",
    )
    assert edited.status_code == 200, edited.json()
    body = edited.json()
    assert body["gross"] == 340_000 and body["slip"]["employee"] == []
    assert body["net"] == 290_000 and body["total"] == 290_000

    # Contributions: only the owner turns them on; draft periods are recomputed.
    assert (
        accountant.patch(
            reverse("pay-settings"), {"contributions_enabled": True}, format="json"
        ).status_code
        == 403
    )
    settings = owner.patch(
        reverse("pay-settings"),
        {"contributions_enabled": True, "employer_cnps": "CNPS-999", "signatory": "Le gérant"},
        format="json",
    )
    assert settings.status_code == 200
    with tenant_context(org_a):
        line.refresh_from_db()
        codes = [c["code"] for c in line.slip["employee"]]
    assert codes[:2] == ["cnps", "irpp"] and line.net < 290_000

    pdf = accountant.get(reverse("pay-line-statement", args=[line.pk]))
    text = pdf_text(pdf.content)
    assert "BULLETIN DE PAIE" in text and "Awa Sangaré" in text and "123-456-789" in text
    assert "Heures supplémentaires" in text and "IRPP" in text and "CNPS-999" in text
    assert "PROVISOIRE" in text and "Cumuls de l’année" in text
    every = accountant.get(reverse("pay-period-payslips", args=[made.pk]))
    assert every.status_code == 200 and every.content.startswith(b"%PDF")

    planner = client_for(make_member(org_a, Role.PLANNER), org_a)
    assert planner.get(reverse("pay-line-statement", args=[line.pk])).status_code == 403
    assert planner.get(reverse("pay-settings")).status_code == 403


def test_daily_slip_with_bonus_and_deduction(
    client_for: Callable[..., APIClient],
    org_a: Organization,
    owner_a: User,
) -> None:
    booked = reservation(org_a, owner_a, -1)
    brice = person(org_a, "Brice Ndzana", "daily", 8000)
    with tenant_context(org_a):
        assignment, _ = services.assign(
            booked, brice, step="event", role="Manutention", user=owner_a
        )
        services.check_in(assignment, user=owner_a, at=assignment.start)
        services.check_out(assignment, user=owner_a, at=assignment.start + timedelta(hours=8))
    owner = client_for(owner_a, org_a)
    day = (timezone.localdate() - timedelta(days=1)).isoformat()

    paid = owner.post(
        reverse("staff-payment-list"),
        {
            "date": day,
            "reservation": str(booked.pk),
            "method": "cash",
            "lines": [
                {
                    "staff": str(brice.pk),
                    "base": 8000,
                    "hours": "8",
                    "items": [
                        {"label": "Prime de nuit", "amount": 2000, "kind": "gain"},
                        {"label": "Avance", "amount": 1500, "kind": "deduction"},
                    ],
                }
            ],
        },
        format="json",
    )
    assert paid.status_code == 201, paid.json()
    payment = paid.json()[0]
    assert (payment["base"], payment["amount"], payment["hours"]) == (8000, 8500, 8.0)

    slip = owner.get(reverse("staff-payment-slip", args=[payment["id"]]))
    text = pdf_text(slip.content)
    assert "FICHE DE PAIE JOURNALIÈRE" in text and "Brice Ndzana" in text
    assert "Prime de nuit" in text and "8 500" in text and booked.number in text
    all_day = owner.get(reverse("pay-day-slips"), {"date": day})
    assert all_day.status_code == 200 and all_day.content.startswith(b"%PDF")
    assert (
        owner.get(reverse("pay-day-slips"), {"date": timezone.localdate().isoformat()}).status_code
        == 404
    )
    assert Decimal(payment["hours"]) == 8


def test_the_accountant_sets_a_salary_from_the_pay_screen(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
) -> None:
    joel = person(org_a, "Joël Mbarga", "monthly", 0, kind="employee")
    today = timezone.localdate()
    with tenant_context(org_a):
        period = services.create_period(today.replace(day=1), today, user=owner_a)
        # Listed although no salary is typed yet: the line is where to set it.
        assert period.lines.filter(staff=joel).exists()
    accountant = client_for(make_member(org_a, Role.ACCOUNTANT), org_a)

    done = accountant.patch(
        reverse("staff-salary", args=[joel.pk]), {"pay_rate": 180_000}, format="json"
    )

    assert done.status_code == 200 and done.json()["pay_rate"] == 180_000
    with tenant_context(org_a):
        assert period.lines.get(staff=joel).base > 0
    planner = client_for(make_member(org_a, Role.PLANNER), org_a)
    assert (
        planner.patch(reverse("staff-salary", args=[joel.pk]), {"pay_rate": 1}).status_code == 403
    )
