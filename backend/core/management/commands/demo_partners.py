"""Demo partner equipment (feedback 14/11/2026): what two partners lend to complete the stock,
including an item the agency does not own at all. All fictitious. Idempotent: existing offers
are left as they are."""

from __future__ import annotations

from stock.models import Item, ItemCategory, PartnerSupply
from vendors.models import Vendor

DECO = {
    "name": "Déco Prestige Douala",
    "kind": "partner",
    "category": "rental",
    "contact_name": "Mireille Ndongo",
    "phone": "+237 699 12 34 56",
    "whatsapp": "+237 699 12 34 56",
    "city": "Douala",
    "address": "Rue Njo-Njo, Bonapriso",
    "payment_terms": "Paiement à la restitution du matériel",
    "services": "Location de décoration et de mobilier en complément pour les grands mariages.",
}
# (partner, item, quantity it lends, price per unit charged to the agency)
SUPPLIES = [
    ("Location Matériel Bonabéri", "Chaise Napoléon dorée", 300, 600),
    ("Location Matériel Bonabéri", "Table ronde 10 personnes", 20, 2500),
    ("Location Matériel Bonabéri", "Nappe ronde blanche", 40, 1000),
    ("Déco Prestige Douala", "Housse de chaise lycra", 300, 250),
    ("Déco Prestige Douala", "Arche florale ronde", 2, 35000),
    ("Déco Prestige Douala", "Chandelier 5 branches", 20, 2000),
]
# Equipment only partners have: the agency rents it to its clients without owning it.
PARTNER_ONLY = [
    ("Location Matériel Bonabéri", "Tente de réception 10 × 20 m", "Décoration", 250000, 2, 150000),
]


def seed() -> int:
    created = 0
    if not Vendor.objects.filter(name=DECO["name"]).exists():
        Vendor.objects.create(**DECO)
    vendors = {v.name: v for v in Vendor.objects.filter(kind=Vendor.Kind.PARTNER)}
    rows = list(SUPPLIES)
    for vendor_name, name, category, rent, quantity, cost in PARTNER_ONLY:
        if not Item.objects.filter(name=name).exists():
            category_obj = ItemCategory.objects.filter(name=category).first()
            if category_obj is None:
                continue
            Item.objects.create(
                name=name,
                category=category_obj,
                reference=f"PART-{Item.objects.count() + 1:03d}",
                rent_price=rent,
            )
        rows.append((vendor_name, name, quantity, cost))
    for vendor_name, item_name, quantity, cost in rows:
        vendor = vendors.get(vendor_name)
        item = Item.objects.filter(name=item_name).first()
        if vendor is None or item is None:
            continue
        _, made = PartnerSupply.objects.get_or_create(
            item=item, vendor=vendor, defaults={"quantity": quantity, "unit_cost": cost}
        )
        created += int(made)
    return created
