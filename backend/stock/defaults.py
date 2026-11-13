"""Default item categories (reservations-stock.md §5.1) with their cleaning delay in days."""

from __future__ import annotations

from .models import ItemCategory

DEFAULT_ITEM_CATEGORIES = [
    ("Mobilier", 0),
    ("Linge de table", 1),  # pressing
    ("Vaisselle", 1),  # washing
    ("Décoration", 0),
    ("Structures et tentes", 0),
    ("Éclairage", 0),
    ("Sonorisation", 0),
    ("Énergie", 0),
    ("Divers", 0),
]


def ensure_item_categories() -> int:
    existing = set(ItemCategory.objects.values_list("name", flat=True))
    created = 0
    for position, (name, cleaning_days) in enumerate(DEFAULT_ITEM_CATEGORIES):
        if name not in existing:
            ItemCategory.objects.create(name=name, cleaning_days=cleaning_days, position=position)
            created += 1
    return created
