"""Sample catalog created with every new space (CLAUDE.md §5): a starting point to edit.

Indicative prices in FCFA for Abidjan; the planner adjusts them in the catalog.
"""

from __future__ import annotations

from .models import QuantityRule, ServiceCategory, ServiceItem, Unit

SAMPLE_CATALOG: list[tuple[str, list[tuple[str, str, int]]]] = [
    (
        "Coordination",
        [
            ("Coordination le jour J", Unit.FLAT, 500_000),
            ("Accompagnement complet (6 mois)", Unit.FLAT, 1_500_000),
        ],
    ),
    (
        "Décoration",
        [
            ("Décoration de salle", Unit.FLAT, 900_000),
            ("Centre de table floral", Unit.UNIT, 25_000),
            ("Arche de cérémonie", Unit.FLAT, 250_000),
        ],
    ),
    (
        "Restauration",
        [
            ("Menu traiteur ivoirien", Unit.GUEST, 12_000),
            ("Pièce montée", Unit.FLAT, 150_000),
            ("Service boissons", Unit.GUEST, 3_500),
        ],
    ),
    (
        "Animation",
        [("DJ et sonorisation", Unit.EVENING, 350_000), ("Orchestre", Unit.EVENING, 700_000)],
    ),
    ("Image", [("Photographe", Unit.DAY, 300_000), ("Vidéaste", Unit.DAY, 350_000)]),
    (
        "Logistique",
        [("Location de chaises", Unit.UNIT, 1_000), ("Transport des mariés", Unit.FLAT, 150_000)],
    ),
    (
        "Invitations",
        [("Faire-part imprimé", Unit.UNIT, 1_500), ("Invitation électronique", Unit.GUEST, 500)],
    ),
]


# Services pre-filled in a new quote, and quantity rules other than « 1 » (complement §9).
DEFAULT_SERVICES = {"Accompagnement complet (6 mois)", "Décoration de salle", "DJ et sonorisation"}
QUANTITY_RULES = {
    "Location de chaises": QuantityRule.PER_GUEST,
    "Centre de table floral": QuantityRule.PER_TEN_GUESTS,
}


def create_sample_catalog() -> None:
    """Runs inside ``tenant_context(organization)``."""
    for order, (category_name, items) in enumerate(SAMPLE_CATALOG):
        category = ServiceCategory.objects.create(name=category_name, order=order)
        for name, unit, price in items:
            ServiceItem.objects.create(
                category=category,
                name=name,
                unit=unit,
                unit_price=price,
                is_default=name in DEFAULT_SERVICES,
                quantity_rule=QUANTITY_RULES.get(name, QuantityRule.ONE),
            )
