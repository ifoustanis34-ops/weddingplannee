"""Dashboard redesign (reservations-stock.md §8): every figure checked against known data."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from typing import Any

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Membership, User
from contracts import services as contract_services
from contracts.models import Contract
from core.tenant import tenant_context
from events.models import Task, Wedding
from finance.defaults import ensure_expense_categories
from finance.models import Expense, ExpenseCategory
from finance.periods import resolve
from finance.tests.test_finance import make_contract
from organizations.models import Organization
from quotes.models import Quote

pytestmark = pytest.mark.django_db
URL = reverse("dashboard-summary")


@pytest.fixture(autouse=True)
def _categories(org_a: Organization, org_b: Organization) -> None:
    """Signup creates the default categories; factory-made organizations need them too."""
    for organization in (org_a, org_b):
        with tenant_context(organization):
            ensure_expense_categories()


# --- Periods ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("key", "start", "end", "previous_start", "previous_end"),
    [
        ("today", "2026-11-12", "2026-11-12", "2026-11-11", "2026-11-11"),
        ("week", "2026-11-09", "2026-11-15", "2026-11-02", "2026-11-08"),
        ("month", "2026-11-01", "2026-11-30", "2026-10-01", "2026-10-31"),
        ("quarter", "2026-10-01", "2026-12-31", "2026-07-01", "2026-09-30"),
        ("year", "2026-01-01", "2026-12-31", "2025-01-01", "2025-12-31"),
    ],
)
def test_calendar_periods_compare_to_the_previous_one(
    key: str, start: str, end: str, previous_start: str, previous_end: str
) -> None:
    period = resolve(key, date(2026, 11, 12))

    assert (period.start, period.end) == (date.fromisoformat(start), date.fromisoformat(end))
    assert (period.previous_start, period.previous_end) == (
        date.fromisoformat(previous_start),
        date.fromisoformat(previous_end),
    )


def test_custom_period_compares_to_the_same_length_before() -> None:
    period = resolve("custom", date(2026, 11, 12), date(2026, 3, 1), date(2026, 3, 10))

    assert (period.previous_start, period.previous_end) == (date(2026, 2, 19), date(2026, 2, 28))


def test_custom_period_needs_ordered_dates(
    client_for: Callable[..., APIClient], owner_a: User, org_a: Organization
) -> None:
    client = client_for(owner_a, org_a)

    wrong = client.get(URL, {"period": "custom", "from": "2026-03-10", "to": "2026-03-01"})
    assert wrong.status_code == 400
    assert "to" in wrong.json()["fields"]
    assert client.get(URL, {"period": "decade"}).status_code == 400


# --- Known data -------------------------------------------------------------------------------


def _category(org: Organization, name: str) -> ExpenseCategory:
    with tenant_context(org):
        category: ExpenseCategory = ExpenseCategory.objects.get(name=name)
    return category


@pytest.fixture
def figures(org_a: Organization, owner_a: User) -> dict[str, Any]:
    """This month: two contracts (1 500 000 with 900 000 of costs, 500 000), 700 000 collected,
    a 150 000 general expense; last month: one 1 000 000 contract; quotes: 1 refused."""
    today = timezone.localdate()
    big = make_contract(org_a, owner_a, 1_500_000, name="Awa & Moussa", expenses=900_000)
    small = make_contract(org_a, owner_a, 500_000, name="Famille Ekotto")
    old = make_contract(org_a, owner_a, 1_000_000, name="Mme Ngo Bassong")
    with tenant_context(org_a):
        last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=10)
        Contract.objects.filter(pk=old.pk).update(
            signed_at=timezone.make_aware(datetime.combine(last_month, time(12)))
        )
        # Wedding costs are dated on the 1st of the month: inside the period whatever today is.
        Expense.objects.filter(wedding__contract=big).update(date=today.replace(day=1))
        Expense.objects.create(
            label="Loyer de l’entrepôt",
            amount=150_000,
            date=today,
            category=ExpenseCategory.objects.get(name="Loyer de l’entrepôt"),
        )
        contract_services.record_payment(
            big, amount=450_000, method="cash", user=owner_a, paid_at=today
        )
        contract_services.record_payment(
            small, amount=250_000, method="wave", user=owner_a, paid_at=today
        )
        refused = Quote.objects.filter(contract=small).get()
        Quote.objects.create(
            client=refused.client,
            issue_date=today,
            valid_until=today + timedelta(days=30),
            status=Quote.Status.REFUSED,
            refused_at=timezone.now(),
            number="DV-TEST-0099",
        )
    return {"big": big, "small": small, "old": old, "today": today}


def test_signature_and_performance_follow_the_definitions(
    client_for: Callable[..., APIClient],
    owner_a: User,
    org_a: Organization,
    figures: dict[str, Any],
) -> None:
    data = client_for(owner_a, org_a).get(URL, {"period": "month"}).json()

    signature = data["signature"]
    assert signature["revenue"] == 2_000_000  # 1 500 000 + 500 000 signed this month
    assert signature["revenue_variation"] == 100.0  # vs 1 000 000 last month
    assert signature["collected"] == 700_000
    # Still due on every live contract: 3 000 000 − 700 000.
    assert signature["to_collect"] == 2_300_000
    assert signature["profit"] == 2_000_000 - 900_000 - 150_000

    performance = data["performance"]
    assert performance["utilisation"] is None  # stock module not built yet
    assert performance["margin_avg"] == 55.0  # (2 000 000 − 900 000) ÷ 2 000 000
    assert performance["basket_avg"] == 1_000_000
    assert performance["quote_confirmation"] == 75.0  # 3 accepted this month, 1 refused
    assert data["orders"] == {"confirmed": 0, "pending": 0, "cancelled": 0}  # no reservation

    assert data["material_today"] == {"available": 0, "categories": []}  # no stock yet
    services = {row["name"]: row for row in data["top_services"]}
    assert services["Mariage complet"]["count"] == 3  # the three quotes were accepted this month
    assert data["is_new"] is False


def test_expenses_ring_keeps_colors_by_category(
    client_for: Callable[..., APIClient],
    owner_a: User,
    org_a: Organization,
    figures: dict[str, Any],
) -> None:
    data = client_for(owner_a, org_a).get(URL, {"period": "month"}).json()

    ring = {row["name"]: row for row in data["expenses_by_category"]}
    assert ring["Sous-traitance"]["amount"] == 900_000  # wedding costs (data migration rule)
    assert ring["Sous-traitance"]["slot"] == 1  # largest over 12 months: first color
    assert ring["Loyer de l’entrepôt"]["slot"] == 2
    month = data["monthly"][-1]
    assert (month["income"], month["expenses"], month["profit"]) == (
        700_000,
        1_050_000,
        -350_000,
    )
    assert len(data["monthly"]) == 12


def test_balances_planning_and_alerts(
    client_for: Callable[..., APIClient],
    owner_a: User,
    org_a: Organization,
    figures: dict[str, Any],
) -> None:
    today = figures["today"]
    with tenant_context(org_a):
        # The deposit of the small contract was due 10 days ago: critical alert.
        schedule = figures["small"].schedule.order_by("position").first()
        schedule.due_date = today - timedelta(days=10)
        schedule.amount = 400_000
        schedule.save()
        rest = figures["small"].schedule.order_by("position").last()
        rest.amount = 100_000
        rest.save()
        wedding = Wedding.objects.get(contract=figures["big"])
        wedding.date = today + timedelta(days=3)
        wedding.save()
        Task.objects.create(
            wedding=wedding, title="Confirmer le traiteur", due_date=today, assignee=owner_a
        )
        Task.objects.create(
            wedding=wedding, title="Plan de table", due_date=today - timedelta(days=2)
        )

    data = client_for(owner_a, org_a).get(URL, {"period": "month"}).json()

    assert [b["client_name"] for b in data["balances"]][:2] == ["Awa & Moussa", "Mme Ngo Bassong"]
    kinds = [a["kind"] for a in data["alerts"]]
    assert kinds[0] == "overdue_payment"
    assert data["alerts"][0]["severity"] == "critical"
    assert data["alerts"][0]["amount"] == 150_000  # 400 000 due, 250 000 paid
    assert "wedding_unready" in kinds and "late_tasks" in kinds
    day = next(d for d in data["planning"] if d["date"] == wedding.date.isoformat())
    event = next(i for i in day["items"] if i["kind"] == "event")
    assert event["title"] == "Awa & Moussa"
    assert event["team"] == [owner_a.full_name]
    assert data["today"]["tasks_today"] == 1
    assert data["today"]["weddings_week"] == 1
    assert data["team_today"] == [
        {"name": owner_a.full_name, "total": 1, "done": 0, "status": "todo"}
    ]


# --- Roles, cache, isolation ------------------------------------------------------------------


def test_amounts_never_reach_a_role_that_must_not_see_them(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    figures: dict[str, Any],
) -> None:
    assistant = client_for(make_member(org_a, Membership.Role.ASSISTANT), org_a)
    data = assistant.get(URL, {"period": "month"}).json()
    for key in ("signature", "performance", "monthly", "expenses_by_category", "balances"):
        assert data[key] is None
    assert all(row["revenue"] is None for row in data["top_services"])
    assert not any(a["kind"] == "overdue_payment" for a in data["alerts"])
    assert "orders" in data and data["material_today"] is not None  # quantities stay

    planner = client_for(make_member(org_a, Membership.Role.PLANNER), org_a)
    data = planner.get(URL, {"period": "month"}).json()
    assert data["signature"]["revenue"] == 2_000_000
    assert data["signature"]["profit"] is None
    assert data["performance"]["margin_avg"] is None
    assert data["expenses_by_category"] is None
    assert data["monthly"][-1]["expenses"] is None


def test_every_cached_period_is_dropped_by_a_payment(
    client_for: Callable[..., APIClient],
    owner_a: User,
    org_a: Organization,
    settings: Any,
) -> None:
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "d"},
        "locks": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "l"},
    }
    contract = make_contract(org_a, owner_a, 1_000_000)
    client = client_for(owner_a, org_a)
    assert client.get(URL, {"period": "month"}).json()["signature"]["collected"] == 0
    assert client.get(URL, {"period": "year"}).json()["signature"]["collected"] == 0

    with tenant_context(org_a):
        contract_services.record_payment(
            contract, amount=300_000, method="cash", user=owner_a, paid_at=timezone.localdate()
        )

    assert client.get(URL, {"period": "month"}).json()["signature"]["collected"] == 300_000
    assert client.get(URL, {"period": "year"}).json()["signature"]["collected"] == 300_000


def test_a_new_space_gets_the_empty_state(
    client_for: Callable[..., APIClient], owner_b: User, org_b: Organization
) -> None:
    data = client_for(owner_b, org_b).get(URL).json()

    assert data["is_new"] is True
    assert data["signature"]["revenue"] == 0


def test_organization_b_sees_nothing_of_a(
    client_for: Callable[..., APIClient],
    owner_b: User,
    org_b: Organization,
    figures: dict[str, Any],
) -> None:
    data = client_for(owner_b, org_b).get(URL, {"period": "year"}).json()

    assert data["signature"]["revenue"] == 0
    assert data["balances"] == []
    assert data["top_services"] == []
    assert data["expenses_by_category"] == []


# --- Expense categories and general expenses (§6.2) -------------------------------------------


def test_signup_creates_the_ten_categories() -> None:
    from organizations.services import bootstrap_organization
    from tests.factories import OrganizationFactory

    organization = OrganizationFactory.create(slug="nouvelle-agence")
    bootstrap_organization(organization)

    with tenant_context(organization):
        names = list(ExpenseCategory.objects.values_list("name", flat=True))
    assert len(names) == 10
    assert names[0] == "Achat de matériel" and "Loyer de l’entrepôt" in names


def test_a_general_expense_needs_a_category(
    client_for: Callable[..., APIClient], owner_a: User, org_a: Organization
) -> None:
    client = client_for(owner_a, org_a)
    fuel = _category(org_a, "Transport et carburant")

    missing = client.post(
        "/api/v1/expenses", {"label": "Carburant camion", "amount": 45_000}, format="json"
    )
    assert missing.status_code == 400
    assert "category" in missing.json()["fields"]

    created = client.post(
        "/api/v1/expenses",
        {
            "label": "Carburant camion",
            "amount": 45_000,
            "category": str(fuel.pk),
            "supplier": "Total Riviera",
            "method": "orange_money",
        },
        format="json",
    )
    assert created.status_code == 201, created.json()
    body = created.json()
    assert body["wedding"] is None
    assert body["category_name"] == "Transport et carburant"
    assert body["date"] == timezone.localdate().isoformat()


def test_categories_are_editable_but_not_by_the_planner(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    owner_a: User,
    org_a: Organization,
) -> None:
    client = client_for(owner_a, org_a)
    created = client.post("/api/v1/expense-categories", {"name": "Location de camion"})
    assert created.status_code == 201
    assert client.post("/api/v1/expense-categories", {"name": "marketing"}).status_code == 400
    renamed = client.patch(
        f"/api/v1/expense-categories/{created.json()['id']}", {"is_active": False}, format="json"
    )
    assert renamed.json()["is_active"] is False

    planner = client_for(make_member(org_a, Membership.Role.PLANNER), org_a)
    assert planner.get("/api/v1/expense-categories").status_code == 403


def test_a_category_of_another_agency_is_refused(
    client_for: Callable[..., APIClient],
    owner_b: User,
    org_a: Organization,
    org_b: Organization,
) -> None:
    other = _category(org_a, "Marketing")

    response = client_for(owner_b, org_b).post(
        "/api/v1/expenses",
        {"label": "Affiches", "amount": 10_000, "category": str(other.pk)},
        format="json",
    )

    assert response.status_code == 400
    assert "category" in response.json()["fields"]
    detail = client_for(owner_b, org_b).get(f"/api/v1/expense-categories/{other.pk}")
    assert detail.status_code == 404


def test_reservations_feed_the_dashboard(
    client_for: Callable[..., APIClient], owner_a: User, org_a: Organization
) -> None:
    """A 250-chair reservation confirmed today, delivered in 3 days, half paid."""
    from datetime import datetime, time

    from crm.models import Client
    from reservations import services as reservation_services
    from stock import services as stock_services
    from stock.defaults import ensure_item_categories
    from stock.models import ItemCategory

    def at(days: int, hour: int) -> datetime:
        return timezone.make_aware(
            datetime.combine(timezone.localdate() + timedelta(days=days), time(hour))
        )

    with tenant_context(org_a):
        ensure_item_categories()
        chairs = stock_services.create_item(
            {
                "name": "Chaise Chiavari",
                "category": ItemCategory.objects.get(name="Mobilier"),
                "rent_price": 2000,
                "initial_quantity": 500,
            },
            user=owner_a,
        )
        reservation = reservation_services.create_reservation(
            {
                "client": Client.objects.create(name="Société Orange Events"),
                "title": "Séminaire",
                "delivery_at": at(3, 8),
                "event_start": at(3, 14),
                "event_end": at(3, 22),
                "return_at": at(4, 10),
            },
            [reservation_services.LineInput(kind="rental", item=chairs, quantity=250)],
            user=owner_a,
        )
        reservation_services.confirm(reservation, user=owner_a)
        reservation_services.record_payment(
            reservation,
            amount=250_000,
            method="wave",
            paid_at=timezone.localdate(),
            user=owner_a,
        )

    data = client_for(owner_a, org_a).get(URL, {"period": "year"}).json()

    assert data["signature"]["revenue"] == 500_000
    assert data["signature"]["collected"] == 250_000
    assert data["signature"]["to_collect"] == 250_000
    assert data["orders"]["confirmed"] == 1
    # 250 chairs × 2 days (delivery to return) over 500 chairs × the days of the year.
    days = (
        timezone.localdate().replace(month=12, day=31)
        - timezone.localdate().replace(month=1, day=1)
    ).days + 1
    assert data["performance"]["utilisation"] == round(250 * 2 * 100 / (500 * days), 1)
    kinds = [i["kind"] for d in data["planning"] for i in d["items"]]
    assert {"delivery", "event", "return"} <= set(kinds)
    assert data["balances"][0]["reservation"] == str(reservation.pk)
