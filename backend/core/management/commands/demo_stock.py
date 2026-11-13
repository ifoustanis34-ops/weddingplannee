"""Equipment of the demo agency (reservations-stock.md §11, « Stock »): 30 articles, 4 packs,
a generator away for an oil change, 3 projectors out of service. Idempotent."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from accounts.models import User
from stock import services
from stock.defaults import ensure_item_categories
from stock.models import Item, ItemCategory, ItemUnit, Pack

# category, name, quantity, rent, unit, sale, purchase cost, deposit, threshold, tracked by unit
ARTICLES = [
    ("Mobilier", "Chaise Napoléon dorée", 400, 1500, "event", None, 9000, 500, 50, False),
    ("Mobilier", "Chaise Chiavari transparente", 250, 2000, "event", None, 14000, 500, 40, False),
    ("Mobilier", "Table ronde 10 personnes", 45, 5000, "event", None, 35000, 5000, 6, False),
    ("Mobilier", "Table rectangulaire 2 m", 30, 4000, "event", None, 28000, 5000, 5, False),
    ("Mobilier", "Table d’honneur modulable", 4, 25000, "event", None, 180000, 20000, 1, False),
    ("Mobilier", "Canapé VIP blanc", 6, 30000, "event", None, 250000, 25000, 2, False),
    ("Linge de table", "Nappe ronde blanche", 60, 2500, "event", 6000, 4500, 0, 10, False),
    ("Linge de table", "Chemin de table doré", 80, 1000, "event", 3000, 1500, 0, 10, False),
    ("Linge de table", "Housse de chaise lycra", 500, 500, "event", 1500, 900, 0, 60, False),
    ("Linge de table", "Serviette de table blanche", 400, 200, "event", 800, 500, 0, 50, False),
    ("Vaisselle", "Assiette de présentation dorée", 400, 500, "event", 2500, 1800, 200, 50, False),
    ("Vaisselle", "Assiette plate blanche", 500, 300, "event", 2000, 1200, 100, 60, False),
    ("Vaisselle", "Verre à pied", 500, 300, "event", 1500, 900, 100, 60, False),
    ("Vaisselle", "Flûte à champagne", 300, 300, "event", 1500, 900, 100, 40, False),
    ("Vaisselle", "Couverts (ménagère 1 pers.)", 400, 400, "event", None, 1500, 100, 50, False),
    ("Décoration", "Arche florale ronde", 3, 60000, "event", None, 280000, 30000, 1, False),
    ("Décoration", "Chandelier 5 branches", 40, 4000, "event", 15000, 9000, 2000, 8, False),
    (
        "Décoration",
        "Centre de table fleurs artificielles",
        50,
        7500,
        "event",
        20000,
        12000,
        2000,
        8,
        False,
    ),
    ("Décoration", "Tapis rouge 10 m", 5, 15000, "event", None, 60000, 10000, 1, False),
    ("Décoration", "Vase cylindrique en verre", 60, 2000, "event", 6000, 3500, 1000, 10, False),
    (
        "Structures et tentes",
        "Chapiteau 10 × 20 m",
        2,
        250000,
        "event",
        None,
        2500000,
        100000,
        1,
        False,
    ),
    (
        "Structures et tentes",
        "Tente pagode 5 × 5 m",
        6,
        60000,
        "event",
        None,
        600000,
        30000,
        1,
        False,
    ),
    (
        "Structures et tentes",
        "Estrade modulable 1 × 2 m",
        12,
        15000,
        "event",
        None,
        120000,
        10000,
        2,
        False,
    ),
    ("Éclairage", "Guirlande guinguette 20 m", 20, 10000, "event", 25000, 15000, 3000, 4, False),
    ("Éclairage", "Projecteur LED", 16, 8000, "day", None, 45000, 5000, 3, True),
    ("Éclairage", "Bougie LED (lot de 10)", 30, 5000, "event", 15000, 8000, 1000, 5, False),
    ("Sonorisation", "Sono complète 2 × 1000 W", 3, 75000, "day", None, 900000, 50000, 1, True),
    ("Sonorisation", "Micro sans fil", 6, 10000, "day", None, 60000, 10000, 1, True),
    ("Énergie", "Groupe électrogène 20 kVA", 2, 90000, "day", None, 4500000, 100000, 1, True),
    ("Divers", "Rallonge électrique 25 m", 20, 2000, "event", None, 12000, 2000, 4, False),
]

PACKS = [
    (
        "Pack réception 100 invités",
        290_000,
        [
            ("Chaise Napoléon dorée", 100),
            ("Table ronde 10 personnes", 10),
            ("Nappe ronde blanche", 10),
            ("Housse de chaise lycra", 100),
            ("Centre de table fleurs artificielles", 10),
        ],
    ),
    (
        "Pack réception 250 invités",
        760_000,
        [
            ("Chaise Chiavari transparente", 250),
            ("Table ronde 10 personnes", 25),
            ("Nappe ronde blanche", 25),
            ("Chemin de table doré", 25),
            ("Centre de table fleurs artificielles", 25),
        ],
    ),
    (
        "Pack cérémonie",
        180_000,
        [
            ("Arche florale ronde", 1),
            ("Tapis rouge 10 m", 1),
            ("Chandelier 5 branches", 2),
            ("Chaise Napoléon dorée", 60),
        ],
    ),
    (
        "Pack lumière & son",
        260_000,
        [
            ("Sono complète 2 × 1000 W", 1),
            ("Projecteur LED", 6),
            ("Guirlande guinguette 20 m", 5),
            ("Groupe électrogène 20 kVA", 1),
        ],
    ),
]


def seed(owner: User) -> bool:
    """Run inside the demo tenant. Returns False when the stock already exists."""
    if Item.objects.exists():
        return False
    ensure_item_categories()
    categories = {c.name: c for c in ItemCategory.objects.all()}
    items: dict[str, Item] = {}
    for (
        category,
        name,
        quantity,
        rent,
        rent_unit,
        sale,
        cost,
        deposit,
        threshold,
        tracked,
    ) in ARTICLES:
        items[name] = services.create_item(
            {
                "name": name,
                "category": categories[category],
                "tracking": "unit" if tracked else "quantity",
                "rent_price": rent,
                "rent_unit": rent_unit,
                "sale_price": sale,
                "purchase_cost": cost,
                "deposit": deposit,
                "alert_threshold": threshold,
                "location": f"Allée {list(categories).index(category) + 1}",
                "initial_quantity": quantity,
            },
            user=owner,
        )
    for name, price, components in PACKS:
        services.save_pack(
            None,
            {
                "name": name,
                "price": price,
                "components": [{"item": items[n], "quantity": q} for n, q in components],
            },
            user=owner,
        )
    today = timezone.localdate()
    generator = items["Groupe électrogène 20 kVA"]
    services.start_maintenance(
        generator,
        reason="Vidange et révision",
        unit=generator.units.order_by("serial_number").first(),
        expected_end=today + timedelta(days=4),
        user=owner,
    )
    projector = items["Projecteur LED"]
    for unit in projector.units.order_by("-serial_number")[:3]:
        services.record_movement(
            projector,
            kind="breakage",
            quantity=1,
            unit=unit,
            reason="Lampe grillée, carte d’alimentation à remplacer",
            user=owner,
        )
    assert ItemUnit.objects.filter(status=ItemUnit.Status.OUT_OF_SERVICE).count() == 3
    assert Pack.objects.count() == len(PACKS)
    return True
