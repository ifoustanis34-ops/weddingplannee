"""Partner equipment (feedback 14/11/2026): what each partner can lend, at what cost."""

from __future__ import annotations

from typing import Any

from django.db import IntegrityError, transaction

from accounts.models import User
from core.exceptions import BusinessError
from vendors.models import Vendor

from .models import Item, ItemCategory, PartnerSupply
from .services import create_item

SUPPLY_FIELDS = ("quantity", "unit_cost", "notes", "is_active")


def _check_partner(vendor: Vendor) -> None:
    if vendor.is_deleted:
        raise BusinessError("invalid", "Ce partenaire a été supprimé.", {"vendor": ["Supprimé."]})


@transaction.atomic
def create_supply(data: dict[str, Any], *, user: User) -> PartnerSupply:
    """An existing item, or a new one the agency does not own (stock 0, partner only)."""
    vendor: Vendor = data["vendor"]
    _check_partner(vendor)
    item: Item | None = data.get("item")
    if item is None:
        category: ItemCategory = data["new_item_category"]
        name = " ".join(str(data["new_item_name"]).split())
        item = Item.objects.filter(name__iexact=name).first() or create_item(
            {
                "name": name,
                "category": category,
                "rent_price": data.get("new_item_rent_price") or 0,
            },
            user=user,
        )
    if vendor.kind != Vendor.Kind.PARTNER:
        # A supplier that starts lending equipment becomes a partner of the agency.
        vendor.kind = Vendor.Kind.PARTNER
        vendor.save(update_fields=["kind", "updated_at"])
    supply = PartnerSupply(item=item, vendor=vendor, created_by=user)
    for field in SUPPLY_FIELDS:
        if field in data:
            setattr(supply, field, data[field])
    try:
        with transaction.atomic():
            supply.save()
    except IntegrityError as exc:
        raise BusinessError(
            "invalid",
            f"{vendor.name} prête déjà « {item.name} » : modifiez la ligne existante.",
            {"item": ["Déjà enregistré pour ce partenaire."]},
        ) from exc
    return supply


@transaction.atomic
def update_supply(supply: PartnerSupply, data: dict[str, Any]) -> PartnerSupply:
    for field in SUPPLY_FIELDS:
        if field in data:
            setattr(supply, field, data[field])
    supply.save()
    return supply


@transaction.atomic
def delete_supply(supply: PartnerSupply) -> bool:
    """Gone for good when no reservation used it; else turned off (the history stays).
    Returns whether it was deleted."""
    if supply.reservation_lines.exists():
        supply.is_active = False
        supply.save(update_fields=["is_active", "updated_at"])
        return False
    supply.delete()
    return True
