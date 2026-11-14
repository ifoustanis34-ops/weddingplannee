"""Equipment lent by partners (feedback 14/11/2026): our stock + what partners complete."""

from __future__ import annotations

import io
from collections.abc import Callable, Sequence
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Membership, User
from core.exceptions import BusinessError
from core.tenant import tenant_context
from finance.periods import Period
from finance.profitability import by_event
from organizations.models import Organization
from reservations import partners, services
from reservations.models import Reservation
from reservations.tests.test_reservations import _defaults, item, rental, reserve  # noqa: F401
from stock.models import Item, ItemCategory, PartnerSupply, StockMovement
from vendors.models import Vendor

pytestmark = pytest.mark.django_db
Status = Reservation.Status


def partner(org: Organization, name: str = "Déco Prestige") -> Vendor:
    with tenant_context(org):
        vendor: Vendor = Vendor.objects.create(
            name=name, kind=Vendor.Kind.PARTNER, category=Vendor.Category.RENTAL
        )
    return vendor


def supply(
    org: Organization, target: Item, vendor: Vendor, quantity: int, cost: int
) -> PartnerSupply:
    with tenant_context(org):
        created: PartnerSupply = PartnerSupply.objects.create(
            item=target, vendor=vendor, quantity=quantity, unit_cost=cost
        )
    return created


def assign(
    org: Organization,
    user: User,
    reservation: Reservation,
    source: PartnerSupply | None,
    quantity: int,
) -> None:
    with tenant_context(org):
        line = reservation.lines.get(kind="rental")
        partners.assign(reservation, line, source, quantity, user=user)


def confirm(org: Organization, user: User, reservation: Reservation) -> Reservation:
    with tenant_context(org):
        return services.confirm(reservation, user=user)


# --- Reservations -------------------------------------------------------------------------------


def test_a_partner_completes_our_stock(org_a: Organization, owner_a: User) -> None:
    chairs = item(org_a, owner_a, "Chaise Chiavari", 200)
    deco = supply(org_a, chairs, partner(org_a), 300, 700)
    reservation = reserve(org_a, owner_a, [rental(chairs, 450)])

    with tenant_context(org_a), pytest.raises(BusinessError) as refused:
        services.confirm(reservation, user=owner_a)
    assert refused.value.error_code == "stock_insufficient"

    assign(org_a, owner_a, reservation, deco, 250)
    confirmed = confirm(org_a, owner_a, reservation)
    assert confirmed.status in (Status.AWAITING_DEPOSIT, Status.CONFIRMED)
    with tenant_context(org_a):
        line = confirmed.lines.get()
        assert (line.partner_quantity, line.partner_unit_cost) == (250, 700)
        assert services.needs(confirmed) == {str(chairs.pk): 200}
        assert partners.cost(confirmed) == 175_000


def test_a_partner_never_lends_more_than_it_has(org_a: Organization, owner_a: User) -> None:
    chairs = item(org_a, owner_a, "Chaise Chiavari", 0)
    deco = supply(org_a, chairs, partner(org_a), 300, 700)
    first = reserve(org_a, owner_a, [rental(chairs, 200)], start=10)
    assign(org_a, owner_a, first, deco, 200)
    confirm(org_a, owner_a, first)

    same_day = reserve(org_a, owner_a, [rental(chairs, 150)], start=10)
    with tenant_context(org_a), pytest.raises(BusinessError) as refused:
        partners.assign(same_day, same_day.lines.get(), deco, 150, user=owner_a)
    assert refused.value.error_code == "partner_insufficient"
    assign(org_a, owner_a, same_day, deco, 100)  # what is left

    other_week = reserve(org_a, owner_a, [rental(chairs, 300)], start=30)
    assign(org_a, owner_a, other_week, deco, 300)  # the partner has them all again
    confirm(org_a, owner_a, other_week)


def test_confirmation_checks_the_partner_again(org_a: Organization, owner_a: User) -> None:
    chairs = item(org_a, owner_a, "Chaise Chiavari", 0)
    deco = supply(org_a, chairs, partner(org_a), 100, 700)
    a = reserve(org_a, owner_a, [rental(chairs, 80)])
    b = reserve(org_a, owner_a, [rental(chairs, 80)])
    assign(org_a, owner_a, a, deco, 80)
    assign(org_a, owner_a, b, deco, 80)  # both drafts: nothing committed yet
    confirm(org_a, owner_a, a)
    with tenant_context(org_a), pytest.raises(BusinessError) as refused:
        services.confirm(b, user=owner_a)
    assert refused.value.error_code == "partner_insufficient"


def test_only_our_part_leaves_the_warehouse(org_a: Organization, owner_a: User) -> None:
    chairs = item(org_a, owner_a, "Chaise Chiavari", 200)
    deco = supply(org_a, chairs, partner(org_a), 300, 700)
    reservation = reserve(org_a, owner_a, [rental(chairs, 260)], deposit_pct=0)
    assign(org_a, owner_a, reservation, deco, 60)
    confirm(org_a, owner_a, reservation)
    with tenant_context(org_a):
        services.checkout(reservation, None, user=owner_a)
        line = reservation.lines.get()
        assert line.quantity_out == 200
        out = StockMovement.objects.get(kind=StockMovement.Kind.CHECKOUT)
        assert out.quantity == 200
        services.process_return(reservation, {}, user=owner_a)
        assert Item.objects.get(pk=chairs.pk).total_quantity == 200


def test_editing_the_lines_keeps_the_partner_part(org_a: Organization, owner_a: User) -> None:
    chairs = item(org_a, owner_a, "Chaise Chiavari", 100)
    deco = supply(org_a, chairs, partner(org_a), 300, 700)
    reservation = reserve(org_a, owner_a, [rental(chairs, 250)])
    assign(org_a, owner_a, reservation, deco, 150)
    with tenant_context(org_a):
        services.update_reservation(reservation, {}, [rental(chairs, 120)], user=owner_a)
        line = reservation.lines.get()
        assert (line.partner_supply_id, line.partner_quantity) == (deco.pk, 120)


def test_profitability_counts_what_partners_charge(org_a: Organization, owner_a: User) -> None:
    chairs = item(org_a, owner_a, "Chaise Chiavari", 0, rent=1500)
    deco = supply(org_a, chairs, partner(org_a), 300, 700)
    reservation = reserve(org_a, owner_a, [rental(chairs, 100)], deposit_pct=0)
    assign(org_a, owner_a, reservation, deco, 100)
    confirm(org_a, owner_a, reservation)
    with tenant_context(org_a):
        reservation.refresh_from_db()
        day = timezone.localdate(reservation.event_start)
        period = Period("custom", day - timedelta(days=1), day + timedelta(days=1), day, day)
        row = next(r for r in by_event(period) if r["id"] == str(reservation.pk))
    assert row["partner_costs"] == 70_000
    assert row["margin"] == reservation.total - 70_000


# --- API ----------------------------------------------------------------------------------------


def test_shortages_suggest_partners_and_the_line_can_be_split(
    org_a: Organization, owner_a: User, client_for: Callable[..., APIClient]
) -> None:
    chairs = item(org_a, owner_a, "Chaise Chiavari", 200)
    deco = supply(org_a, chairs, partner(org_a), 300, 700)
    reservation = reserve(org_a, owner_a, [rental(chairs, 450)])
    api = client_for(owner_a, org_a)

    shortage = api.get(reverse("reservation-shortages", args=[reservation.pk])).json()[0]
    assert shortage["partners"] == [
        {
            "supply": str(deco.pk),
            "vendor": str(deco.vendor_id),
            "vendor_name": "Déco Prestige",
            "free": 300,
            "unit_cost": 700,
        }
    ]
    response = api.post(
        reverse("reservation-line-partner", args=[reservation.pk, shortage["line"]]),
        {"supply": str(deco.pk), "quantity": 250},
        format="json",
    )
    assert response.status_code == 200
    line = response.json()["lines"][0]
    assert (line["partner_name"], line["partner_quantity"]) == ("Déco Prestige", 250)
    assert api.get(reverse("reservation-shortages", args=[reservation.pk])).json() == []

    orders = api.get(reverse("reservation-partner-orders", args=[reservation.pk])).json()
    assert orders[0]["vendor_name"] == "Déco Prestige" and orders[0]["total"] == 175_000
    pdf = api.get(
        reverse("reservation-document", args=[reservation.pk]),
        {"type": "partner", "vendor": str(deco.vendor_id)},
    )
    assert pdf.status_code == 200 and pdf["Content-Type"] == "application/pdf"


def test_the_planner_books_partners_without_seeing_their_price(
    org_a: Organization,
    owner_a: User,
    make_member: Callable[..., User],
    client_for: Callable[..., APIClient],
) -> None:
    planner = make_member(org_a, Membership.Role.PLANNER, email="planner@agence-a.ci")
    chairs = item(org_a, owner_a, "Chaise Chiavari", 0)
    deco = supply(org_a, chairs, partner(org_a), 300, 700)
    reservation = reserve(org_a, owner_a, [rental(chairs, 50)])
    api = client_for(planner, org_a)
    shortage = api.get(reverse("reservation-shortages", args=[reservation.pk])).json()[0]
    assert shortage["partners"][0]["unit_cost"] is None
    line = api.post(
        reverse("reservation-line-partner", args=[reservation.pk, shortage["line"]]),
        {"supply": str(deco.pk), "quantity": 50},
        format="json",
    ).json()["lines"][0]
    assert line["partner_quantity"] == 50 and line["partner_unit_cost"] is None
    assert api.get(reverse("partner-supplies")).json()[0]["unit_cost"] is None


def test_partner_supplies_api(
    org_a: Organization, owner_a: User, client_for: Callable[..., APIClient]
) -> None:
    vendor = partner(org_a)
    api = client_for(owner_a, org_a)
    with tenant_context(org_a):
        category = ItemCategory.objects.get(name="Mobilier")
    created = api.post(
        reverse("partner-supplies"),
        {
            "vendor": str(vendor.pk),
            "new_item_name": "Arche florale",
            "new_item_category": str(category.pk),
            "new_item_rent_price": 75000,
            "quantity": 2,
            "unit_cost": 40000,
        },
        format="json",
    )
    assert created.status_code == 201, created.json()
    body = created.json()
    assert (body["item_name"], body["own_quantity"], body["quantity"]) == ("Arche florale", 0, 2)
    items = api.get(reverse("item-list"), {"source": "partner"}).json()
    assert [(i["name"], i["partner_quantity"]) for i in items] == [("Arche florale", 2)]
    assert api.get(reverse("item-list"), {"source": "own"}).json() == []
    deleted = api.delete(reverse("partner-supply", args=[body["id"]])).json()
    assert deleted == {"deleted": True}


def test_another_agency_never_sees_the_partners(
    org_a: Organization,
    org_b: Organization,
    owner_a: User,
    owner_b: User,
    client_for: Callable[..., APIClient],
) -> None:
    chairs = item(org_a, owner_a, "Chaise Chiavari", 0)
    supply(org_a, chairs, partner(org_a), 300, 700)
    assert client_for(owner_b, org_b).get(reverse("partner-supplies")).json() == []


# --- Import -------------------------------------------------------------------------------------


def sheet(rows: Sequence[Sequence[object]]) -> SimpleUploadedFile:
    from openpyxl import Workbook

    workbook = Workbook()
    active = workbook.active
    assert active is not None
    for row in rows:
        active.append(list(row))
    buffer = io.BytesIO()
    workbook.save(buffer)
    return SimpleUploadedFile("materiel.xlsx", buffer.getvalue())


HEADERS = [
    "Type",
    "Article",
    "Catégorie",
    "Quantité",
    "Prix location",
    "Partenaire",
    "Prix partenaire",
]


def test_import_both_lists_with_a_preview_first(
    org_a: Organization, owner_a: User, client_for: Callable[..., APIClient]
) -> None:
    chairs = item(org_a, owner_a, "Chaise Chiavari", 120)
    api = client_for(owner_a, org_a)
    rows: list[Sequence[object]] = [
        HEADERS,
        ["Interne", "chaise chiavari", "Mobilier", 200, 1500, "", ""],
        ["Interne", "Nappe blanche", "Linge de table", 80, 800, "", ""],
        ["Partenaire", "Chaise Chiavari", "Mobilier", 300, "", "Déco Prestige", 700],
        ["Partenaire", "Arche florale", "Décoration", 2, 75000, "Fleurs du Wouri", 40000],
    ]
    preview = api.post(
        reverse("stock-import") + "?dry_run=true", {"file": sheet(rows)}, format="multipart"
    ).json()
    assert preview["errors"] == [] and preview["dry_run"] is True
    with tenant_context(org_a):
        assert not PartnerSupply.objects.exists()
        assert Item.objects.get(pk=chairs.pk).total_quantity == 120

    report = api.post(reverse("stock-import"), {"file": sheet(rows)}, format="multipart").json()
    assert report["errors"] == []
    assert (report["items_created"], report["partners_created"], report["supplies_created"]) == (
        2,
        2,
        2,
    )
    with tenant_context(org_a):
        assert Item.objects.get(pk=chairs.pk).total_quantity == 200  # exactly the list
        assert Item.objects.get(name="Nappe blanche").total_quantity == 80
        arch = Item.objects.get(name="Arche florale")
        assert arch.total_quantity == 0
        assert PartnerSupply.objects.get(item=arch).unit_cost == 40000
        assert Vendor.objects.get(name="Fleurs du Wouri").kind == Vendor.Kind.PARTNER


def test_import_saves_nothing_when_a_line_is_wrong(
    org_a: Organization, owner_a: User, client_for: Callable[..., APIClient]
) -> None:
    api = client_for(owner_a, org_a)
    report = api.post(
        reverse("stock-import"),
        {
            "file": sheet(
                [
                    HEADERS,
                    ["Interne", "Nappe blanche", "Linge de table", 80, 800, "", ""],
                    ["Interne", "Chaise", "Mobilier", "beaucoup", 1500, "", ""],
                ]
            )
        },
        format="multipart",
    ).json()
    assert report["errors"] == ["ligne 3 : « Quantité » n’est pas un nombre (beaucoup)."]
    with tenant_context(org_a):
        assert not Item.objects.filter(name="Nappe blanche").exists()


def test_only_the_owner_imports(
    org_a: Organization, make_member: Callable[..., User], client_for: Callable[..., APIClient]
) -> None:
    keeper = make_member(org_a, Membership.Role.STOREKEEPER, email="stock@agence-a.ci")
    response = client_for(keeper, org_a).post(
        reverse("stock-import"), {"file": sheet([HEADERS])}, format="multipart"
    )
    assert response.status_code == 403
    template = client_for(keeper, org_a).get(reverse("stock-template"))
    assert template.status_code == 200
