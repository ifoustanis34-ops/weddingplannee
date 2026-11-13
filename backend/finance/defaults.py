"""Default expense categories (reservations-stock.md §6.2), created with every space."""

from __future__ import annotations

from .models import ExpenseCategory

DEFAULT_EXPENSE_CATEGORIES = [
    "Achat de matériel",
    "Maintenance et réparation",
    "Transport et carburant",
    "Salaires et journaliers",
    "Sous-traitance",
    "Loyer de l’entrepôt",
    "Électricité et eau",
    "Marketing",
    "Frais bancaires et Mobile Money",
    "Divers",
]
SUBCONTRACTING = "Sous-traitance"


def ensure_expense_categories() -> int:
    """Create the missing default categories in the active organization. Returns how many."""
    existing = set(ExpenseCategory.objects.values_list("name", flat=True))
    created = 0
    for position, name in enumerate(DEFAULT_EXPENSE_CATEGORIES):
        if name not in existing:
            ExpenseCategory.objects.create(name=name, position=position)
            created += 1
    return created
