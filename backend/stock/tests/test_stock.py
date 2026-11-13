"""Stock and equipment (reservations-stock.md §5, §12, §13)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from django.db import connection
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Membership, User
from alerts import services as alert_services
from alerts.models import Alert
from core.exceptions import BusinessError
from core.tenant import tenant_context
from finance.defaults import ensure_expense_categories
from finance.models import Expense
from organizations.models import Organization
from stock import availability, services
from stock.defaults import ensure_item_categories
from stock.models import Item, ItemCategory, ItemUnit, Maintenance, StockMovement

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _defaults(org_a: Organization, org_b: Organization) -> None:
    for organization in (org_a, org_b):
        with tenant_context(organization):
            ensure_item_categories()
            ensure_expense_categories()


def category(org: Organization, name: str = "Mobilier") -> ItemCategory:
    with tenant_context(org):
        found: ItemCategory = ItemCategory.objects.get(name=name)
    return found


def make_item(
    org: Organization, user: User, name: str = "Chaise Napoléon", quantity: int = 100, **extra: Any
) -> Item:
    with tenant_context(org):
        item = services.create_item(
            {
                "name": name,
                "category": ItemCategory.objects.get(name=extra.pop("category", "Mobilier")),
                "rent_price": 1500,
                "purchase_cost": 9000,
                "initial_quantity": quantity,
                **extra,
            },
            user=user,
        )
        item.refresh_from_db()
    return item


def available(org: Organization, item: Item, days: int = 0, span: int = 0) -> int:
    today = timezone.localdate()
    start = today + timedelta(days=days)
    with tenant_context(org):
        item = Item.objects.select_related("category").get(pk=item.pk)
        value = availability.compute([item], start, start + timedelta(days=span), today)
    return value[str(item.pk)].available


# --- Items and references -----------------------------------------------------------------------


def test_references_follow_the_category(org_a: Organization, owner_a: User) -> None:
    first = make_item(org_a, owner_a, "Chaise Napoléon")
    second = make_item(org_a, owner_a, "Table ronde")
    linen = make_item(org_a, owner_a, "Nappe", category="Linge de table")

    assert (first.reference, second.reference, linen.reference) == ("MOB-001", "MOB-002", "LIN-001")
    assert first.total_quantity == 100
    with tenant_context(org_a):
        assert Item.objects.get(pk=linen.pk).delay_days == 1  # pressing (category delay)


def test_numbered_equipment_gets_its_units(org_a: Organization, owner_a: User) -> None:
    sono = make_item(
        org_a,
        owner_a,
        "Sono",
        quantity=2,
        category="Sonorisation",
        tracking="unit",
        serials=["SN-A", "SN-B"],
    )

    with tenant_context(org_a):
        assert list(sono.units.values_list("serial_number", flat=True)) == ["SN-A", "SN-B"]


# --- Availability (§5.2) ------------------------------------------------------------------------


def test_maintenance_blocks_only_its_period(org_a: Organization, owner_a: User) -> None:
    item = make_item(org_a, owner_a, quantity=10)
    with tenant_context(org_a):
        maintenance = services.start_maintenance(
            item,
            reason="Réparation",
            quantity=3,
            expected_end=timezone.localdate() + timedelta(4),
            user=owner_a,
        )

    assert available(org_a, item) == 7
    assert available(org_a, item, days=10) == 10  # back by then
    with tenant_context(org_a):
        Maintenance.objects.filter(pk=maintenance.pk).update(
            expected_end=timezone.localdate() - timedelta(days=1)
        )
    assert available(org_a, item, days=10) == 7  # overdue: nobody knows when it comes back
    with tenant_context(org_a):
        services.close_maintenance(Maintenance.objects.get(pk=maintenance.pk), user=owner_a)
    assert available(org_a, item) == 10


def test_out_of_service_units_and_pack_availability(org_a: Organization, owner_a: User) -> None:
    projector = make_item(
        org_a, owner_a, "Projecteur", quantity=4, category="Éclairage", tracking="unit"
    )
    chairs = make_item(org_a, owner_a, "Chaise", quantity=100)
    with tenant_context(org_a):
        unit = projector.units.first()
        assert unit is not None
        services.record_movement(
            projector, kind="breakage", quantity=1, unit=unit, reason="Lampe", user=owner_a
        )
        pack = services.save_pack(
            None,
            {
                "name": "Pack soirée",
                "price": 100_000,
                "components": [
                    {"item": projector, "quantity": 2},
                    {"item": chairs, "quantity": 40},
                ],
            },
            user=owner_a,
        )
        unit.refresh_from_db()
        assert unit.status == ItemUnit.Status.OUT_OF_SERVICE
        values = availability.compute(
            [projector, chairs], timezone.localdate(), timezone.localdate(), timezone.localdate()
        )
        projector.refresh_from_db()
        packs = availability.pack_available(pack, values)

    assert projector.total_quantity == 4  # still owned
    assert values[str(projector.pk)].available == 3
    assert packs == 1  # 3 // 2 projectors, 100 // 40 chairs


# --- Movements (§5.3) ---------------------------------------------------------------------------


def test_purchase_creates_its_expense_and_cancelling_removes_it(
    org_a: Organization, owner_a: User
) -> None:
    item = make_item(org_a, owner_a, quantity=10)
    with tenant_context(org_a):
        movement = services.record_movement(
            item, kind="purchase", quantity=5, unit_cost=9000, reference="FA-12", user=owner_a
        )
        expense = Expense.objects.get(pk=movement.expense_id)
        assert (expense.amount, expense.category.name) == (45_000, "Achat de matériel")
        item.refresh_from_db()
        assert item.total_quantity == 15

        with pytest.raises(BusinessError):
            services.cancel_movement(movement, reason=" ", user=owner_a, request=None)
        services.cancel_movement(movement, reason="Erreur de saisie", user=owner_a, request=None)
        item.refresh_from_db()
        movement.refresh_from_db()
        assert item.total_quantity == 10
        assert movement.cancelled_at is not None
        assert not Expense.objects.filter(pk=expense.pk).exists()
        assert StockMovement.objects.filter(pk=movement.pk).exists()  # never deleted
        with pytest.raises(BusinessError):
            services.cancel_movement(movement, reason="Encore", user=owner_a, request=None)


def test_a_sale_never_takes_more_than_what_is_here(org_a: Organization, owner_a: User) -> None:
    item = make_item(org_a, owner_a, quantity=10, category="Linge de table", sale_price=6000)
    with tenant_context(org_a):
        services.start_maintenance(item, reason="Pressing", quantity=4, user=owner_a)
        with pytest.raises(BusinessError) as refused:
            services.record_movement(item, kind="sale", quantity=7, user=owner_a)
        assert refused.value.error_code == "stock_insufficient"
        services.record_movement(item, kind="sale", quantity=6, user=owner_a)
        item.refresh_from_db()

    assert item.total_quantity == 4  # a sale removes the quantities for good


def test_maintenance_cost_becomes_an_expense(org_a: Organization, owner_a: User) -> None:
    generator = make_item(org_a, owner_a, "Groupe", quantity=1, category="Énergie", tracking="unit")
    with tenant_context(org_a):
        unit = generator.units.get()
        maintenance = services.start_maintenance(
            generator, reason="Vidange", unit=unit, user=owner_a
        )
        unit.refresh_from_db()
        assert unit.status == ItemUnit.Status.MAINTENANCE
        services.close_maintenance(maintenance, cost=85_000, user=owner_a)
        unit.refresh_from_db()
        maintenance.refresh_from_db()
        expense = maintenance.expense
        assert expense is not None and expense.category is not None
        category_name = expense.category.name

    assert unit.status == ItemUnit.Status.AVAILABLE
    assert category_name == "Maintenance et réparation"


def test_inventory_turns_differences_into_adjustments(org_a: Organization, owner_a: User) -> None:
    chairs = make_item(org_a, owner_a, "Chaise", quantity=100)
    tables = make_item(org_a, owner_a, "Table", quantity=10)
    with tenant_context(org_a):
        inventory = services.start_inventory(user=owner_a, category=chairs.category)
        lines = {line.item_id: line for line in inventory.lines.all()}
        services.count(inventory, {str(lines[chairs.pk].pk): 97, str(lines[tables.pk].pk): 10})
        services.validate_inventory(inventory, user=owner_a, request=None)
        chairs.refresh_from_db()
        adjustment = StockMovement.objects.get(item=chairs, kind="adjustment")

    assert chairs.total_quantity == 97
    assert adjustment.delta == -3


# --- API, roles and isolation (§12) -------------------------------------------------------------


def test_storekeeper_runs_the_stock_without_seeing_any_amount(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
) -> None:
    item = make_item(org_a, owner_a)
    client = client_for(make_member(org_a, Membership.Role.STOREKEEPER), org_a)

    listed = client.get(reverse("item-list")).json()
    assert listed[0]["today"]["available"] == 100
    for key in ("rent_price", "purchase_cost", "deposit", "stock_value"):
        assert listed[0][key] is None
    moved = client.post(
        reverse("movement-list"),
        {"item": str(item.pk), "kind": "purchase", "quantity": 20, "unit_cost": 9000},
        format="json",
    )
    assert moved.status_code == 201, moved.json()
    assert moved.json()["unit_cost"] is None
    with tenant_context(org_a):
        assert not Expense.objects.exists()  # no amount entered by the storekeeper
    assert client.get(reverse("stock-stats")).json()["stock_value"] is None


@pytest.mark.parametrize(
    ("role", "reads", "writes", "costs"),
    [
        (Membership.Role.OWNER, 200, 201, True),
        (Membership.Role.PLANNER, 200, 403, False),
        (Membership.Role.ASSISTANT, 200, 403, False),
        (Membership.Role.ACCOUNTANT, 200, 403, True),
        (Membership.Role.TEAM_LEAD, 403, 403, False),
        (Membership.Role.STAFF, 403, 403, False),
    ],
)
def test_who_reads_and_who_writes(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
    role: str,
    reads: int,
    writes: int,
    costs: bool,
) -> None:
    item = make_item(org_a, owner_a)
    member = owner_a if role == Membership.Role.OWNER else make_member(org_a, role)
    client = client_for(member, org_a)

    response = client.get(reverse("item-detail", args=[item.pk]))
    assert response.status_code == reads
    if reads == 200:
        assert (response.json()["purchase_cost"] is not None) is costs
    created = client.post(
        reverse("item-list"),
        {"name": "Tabouret", "category": str(category(org_a).pk)},
        format="json",
    )
    assert created.status_code == writes


def test_organization_b_cannot_reach_the_stock_of_a(
    client_for: Callable[..., APIClient],
    org_a: Organization,
    owner_a: User,
    org_b: Organization,
    owner_b: User,
) -> None:
    item = make_item(org_a, owner_a)
    other = client_for(owner_b, org_b)

    assert other.get(reverse("item-list")).json() == []
    assert other.get(reverse("item-detail", args=[item.pk])).status_code == 404
    assert (
        other.patch(
            reverse("item-detail", args=[item.pk]), {"name": "Pirate"}, format="json"
        ).status_code
        == 404
    )
    moved = other.post(
        reverse("movement-list"),
        {"item": str(item.pk), "kind": "sale", "quantity": 1},
        format="json",
    )
    assert moved.status_code == 400 and "item" in moved.json()["fields"]
    assert other.get(reverse("item-labels", args=[item.pk])).status_code == 404


def test_cancel_through_the_api_is_audited(
    client_for: Callable[..., APIClient], org_a: Organization, owner_a: User
) -> None:
    item = make_item(org_a, owner_a)
    client = client_for(owner_a, org_a)
    movement = client.post(
        reverse("movement-list"),
        {"item": str(item.pk), "kind": "loss", "quantity": 2, "reason": "Égarées"},
        format="json",
    ).json()

    response = client.post(
        reverse("movement-cancel", args=[movement["id"]]), {"reason": "Retrouvées"}, format="json"
    )

    assert response.json()["cancel_reason"] == "Retrouvées"
    from core.models import AuditLog

    with tenant_context(org_a):
        assert AuditLog.objects.filter(action="stock.movement_cancelled").exists()


def test_grid_labels_and_availability_endpoints(
    client_for: Callable[..., APIClient], org_a: Organization, owner_a: User
) -> None:
    item = make_item(org_a, owner_a, quantity=10)
    with tenant_context(org_a):
        services.start_maintenance(
            item,
            reason="Réparation",
            quantity=5,
            expected_end=timezone.localdate() + timedelta(2),
            user=owner_a,
        )
    client = client_for(owner_a, org_a)

    grid = client.get(reverse("availability-grid"), {"days": 7}).json()
    rates = grid["rows"][0]["cells"]
    assert [cell["rate"] for cell in rates[:4]] == [50, 50, 50, 0]
    period = client.get(reverse("availability"), {"items": str(item.pk)}).json()
    assert period["items"][0]["available"] == 5
    pdf = client.get(reverse("item-labels", args=[item.pk]), {"count": 3})
    assert pdf["Content-Type"] == "application/pdf" and pdf.content[:4] == b"%PDF"


# --- Alerts (§5.4) ------------------------------------------------------------------------------


def test_stock_alerts_reach_the_storekeeper(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    owner_a: User,
) -> None:
    glasses = make_item(
        org_a, owner_a, "Verre à pied", quantity=70, alert_threshold=60, category="Vaisselle"
    )
    sono = make_item(org_a, owner_a, "Sono", quantity=1, category="Sonorisation", tracking="unit")
    with tenant_context(org_a):
        services.record_movement(glasses, kind="breakage", quantity=12, user=owner_a)
        maintenance = services.start_maintenance(
            sono,
            reason="Ampli",
            unit=sono.units.get(),
            user=owner_a,
            expected_end=timezone.localdate(),
        )
        Maintenance.objects.filter(pk=maintenance.pk).update(
            expected_end=timezone.localdate() - timedelta(days=3)
        )
        alert_services.refresh()
        kinds = {a.kind for a in alert_services.open_alerts()}
    assert {Alert.Kind.BELOW_THRESHOLD, Alert.Kind.MAINTENANCE_LATE} <= kinds

    storekeeper = client_for(make_member(org_a, Membership.Role.STOREKEEPER), org_a)
    seen = {a["kind"] for a in storekeeper.get("/api/v1/alerts").json()["results"]}
    assert seen == {"below_threshold", "maintenance_late"}


def test_stock_tables_are_under_row_level_security() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM pg_class WHERE relname LIKE 'stock\\_%%'"
            " AND relkind = 'r' AND relrowsecurity AND relforcerowsecurity"
        )
        assert cursor.fetchone() == (9,)
