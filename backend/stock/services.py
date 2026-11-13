"""Business rules of the stock (reservations-stock.md §5). Every quantity change happens under
a row lock on the item and leaves an immutable movement."""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Any

from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import User
from core import audit
from core.exceptions import BusinessError
from documents import images
from finance.models import Expense, ExpenseCategory

from . import availability
from .models import (
    Inventory,
    InventoryLine,
    Item,
    ItemCategory,
    ItemUnit,
    Maintenance,
    Pack,
    PackComponent,
    StockMovement,
)

Kind = StockMovement.Kind
# Signed effect of a manual movement on the owned quantity.
DIRECTION = {
    Kind.PURCHASE: 1,
    Kind.SALE: -1,
    Kind.BREAKAGE: -1,
    Kind.LOSS: -1,
}
MANUAL_KINDS = (Kind.PURCHASE, Kind.SALE, Kind.BREAKAGE, Kind.LOSS, Kind.ADJUSTMENT)
UNIT_STATUS_AFTER = {
    Kind.SALE: ItemUnit.Status.SOLD,
    Kind.LOSS: ItemUnit.Status.LOST,
    Kind.BREAKAGE: ItemUnit.Status.OUT_OF_SERVICE,
}
PURCHASE_CATEGORY = "Achat de matériel"
MAINTENANCE_CATEGORY = "Maintenance et réparation"
ITEM_FIELDS = (
    "name",
    "category",
    "description",
    "location",
    "tracking",
    "rent_price",
    "rent_unit",
    "sale_price",
    "purchase_cost",
    "deposit",
    "alert_threshold",
    "cleaning_days",
    "is_active",
)


def today() -> date:
    return timezone.localdate()


# --- Items --------------------------------------------------------------------------------------


def _prefix(category: ItemCategory) -> str:
    plain = unicodedata.normalize("NFD", category.name).encode("ascii", "ignore").decode()
    letters = re.sub(r"[^A-Za-z]", "", plain).upper()
    return (letters[:3] or "ART").ljust(3, "X")


def next_reference(category: ItemCategory) -> str:
    """« MOB-007 »: category prefix and the next free number of that prefix."""
    prefix = _prefix(category)
    numbers = [
        int(match.group(1))
        for reference in Item.objects.filter(reference__startswith=f"{prefix}-").values_list(
            "reference", flat=True
        )
        if (match := re.fullmatch(rf"{prefix}-(\d+)", reference))
    ]
    return f"{prefix}-{max(numbers, default=0) + 1:03d}"


@transaction.atomic
def create_item(data: dict[str, Any], *, user: User) -> Item:
    item = Item(created_by=user)
    for field in ITEM_FIELDS:
        if field in data:
            setattr(item, field, data[field])
    item.reference = (data.get("reference") or "").strip().upper() or next_reference(
        data["category"]
    )
    try:
        with transaction.atomic():
            item.save()
    except IntegrityError as exc:
        raise BusinessError(
            "invalid",
            "Cette référence existe déjà.",
            {"reference": ["Référence déjà utilisée."]},
        ) from exc
    quantity = int(data.get("initial_quantity") or 0)
    if quantity:
        record_movement(
            item,
            kind=Kind.PURCHASE,
            quantity=quantity,
            reason="Stock initial",
            user=user,
            serials=data.get("serials") or [],
            create_expense=False,
        )
        item.refresh_from_db()
    return item


@transaction.atomic
def update_item(item: Item, data: dict[str, Any]) -> Item:
    if "tracking" in data and data["tracking"] != item.tracking and item.total_quantity:
        raise BusinessError(
            "invalid",
            "Le mode de suivi ne change plus une fois du stock enregistré.",
            {"tracking": ["Stock déjà enregistré."]},
        )
    for field in ITEM_FIELDS:
        if field in data:
            setattr(item, field, data[field])
    if data.get("reference"):
        item.reference = data["reference"].strip().upper()
    try:
        with transaction.atomic():
            item.save()
    except IntegrityError as exc:
        raise BusinessError(
            "invalid", "Cette référence existe déjà.", {"reference": ["Référence déjà utilisée."]}
        ) from exc
    return item


def store_photo(item: Item, content: bytes) -> Item:
    """Real image type checked (Pillow), resized to 1200 px, stored under the agency prefix."""
    if images.sniff(content) == "svg":
        raise BusinessError(
            "invalid", "Choisissez une photo (JPEG, PNG ou WebP).", {"file": ["Format refusé."]}
        )
    processed = images.process_raster(content, transparent=False)
    if item.photo:
        item.photo.delete(save=False)
    item.photo.save(f"photo.{processed.extension}", ContentFile(processed.content), save=False)
    item.save(update_fields=["photo", "updated_at"])
    return item


def remove_photo(item: Item) -> Item:
    if item.photo:
        item.photo.delete(save=False)
        item.save(update_fields=["photo", "updated_at"])
    return item


# --- Movements ----------------------------------------------------------------------------------


def _expense(category_name: str, *, label: str, amount: int, day: date, user: User) -> Expense:
    category = ExpenseCategory.objects.filter(name=category_name).first()
    expense: Expense = Expense.objects.create(
        category=category, label=label, amount=amount, date=day, is_paid=True, created_by=user
    )
    return expense


def _available_today(item: Item) -> int:
    return availability.compute([item], today(), today(), today())[str(item.pk)].available


@transaction.atomic
def record_movement(
    item: Item,
    *,
    kind: str,
    quantity: int,
    user: User,
    reason: str = "",
    reference: str = "",
    direction: int = 1,
    unit: ItemUnit | None = None,
    unit_cost: int | None = None,
    serials: list[str] | None = None,
    create_expense: bool = True,
) -> StockMovement:
    """Manual movement (purchase, sale, breakage, loss, adjustment), under a lock on the item.

    A sale, a breakage or a loss never takes more than what is available today; a unit-tracked
    item names its unit; a purchase of unit-tracked equipment creates its numbered units.
    """
    if kind not in MANUAL_KINDS:
        raise BusinessError("invalid", "Type de mouvement inconnu.", {"kind": ["Type inconnu."]})
    if quantity <= 0:
        raise BusinessError("invalid", "La quantité doit être positive.", {"quantity": ["> 0"]})
    item = Item.objects.select_for_update().select_related("category").get(pk=item.pk)
    delta = quantity * (direction if kind == Kind.ADJUSTMENT else DIRECTION[Kind(kind)])

    if item.tracking == Item.Tracking.UNIT:
        if kind == Kind.ADJUSTMENT:
            raise BusinessError(
                "invalid", "Les articles suivis par unité s’ajustent unité par unité."
            )
        if kind == Kind.PURCHASE:
            serials = [s.strip() for s in (serials or []) if s.strip()]
            if serials and len(serials) != quantity:
                raise BusinessError(
                    "invalid",
                    f"Indiquez {quantity} numéros de série, ou aucun pour les numéroter.",
                    {"serials": ["Nombre de numéros différent de la quantité."]},
                )
        else:
            if unit is None or unit.item_id != item.pk or quantity != 1:
                raise BusinessError(
                    "invalid",
                    "Choisissez l’unité concernée (une à la fois).",
                    {"unit": ["Unité obligatoire."]},
                )
            if unit.status not in (ItemUnit.Status.AVAILABLE, ItemUnit.Status.OUT_OF_SERVICE):
                raise BusinessError("invalid", "Cette unité n’est pas au dépôt.")
            if kind == Kind.BREAKAGE:
                delta = 0  # a broken unit stays owned, out of service until repaired or sold

    if delta < 0:
        # An adjustment may take anything owned; a sale, breakage or loss only what is here.
        if kind == Kind.ADJUSTMENT:
            limit = item.total_quantity
        elif item.tracking == Item.Tracking.QUANTITY:
            limit = _available_today(item)
        else:
            limit = 1  # the named unit, checked above
        if -delta > limit:
            raise BusinessError(
                "stock_insufficient",
                f"Seulement {limit} disponible(s) aujourd’hui pour « {item.name} ».",
                {"quantity": [f"Maximum {limit}"]},
            )

    expense = None
    if kind == Kind.PURCHASE and unit_cost and create_expense:
        expense = _expense(
            PURCHASE_CATEGORY,
            label=f"Achat : {item.name} × {quantity}",
            amount=unit_cost * quantity,
            day=today(),
            user=user,
        )
    movement: StockMovement = StockMovement.objects.create(
        item=item,
        unit=unit,
        kind=kind,
        delta=delta,
        quantity=quantity,
        reason=reason.strip(),
        reference=reference.strip(),
        unit_cost=unit_cost,
        expense=expense,
        author=user,
        occurred_at=timezone.now(),
        created_by=user,
    )
    item.total_quantity += delta
    item.save(update_fields=["total_quantity", "updated_at"])

    if item.tracking == Item.Tracking.UNIT:
        if kind == Kind.PURCHASE:
            existing = item.units.count()
            for index in range(quantity):
                serial = (
                    serials[index] if serials else f"{item.reference}-{existing + index + 1:02d}"
                )
                ItemUnit.objects.create(item=item, serial_number=serial, created_by=user)
        elif unit is not None:
            unit.status = UNIT_STATUS_AFTER[Kind(kind)]
            if kind == Kind.BREAKAGE:
                unit.condition = ItemUnit.Condition.DAMAGED
            unit.save(update_fields=["status", "condition", "updated_at"])
    return movement


@transaction.atomic
def cancel_movement(movement: StockMovement, *, reason: str, user: User, request: Any) -> None:
    """Never deleted: cancelled with a reason, its effect reversed, traced in the audit log."""
    reason = reason.strip()
    if not reason:
        raise BusinessError(
            "invalid", "Indiquez pourquoi ce mouvement est annulé.", {"reason": ["Obligatoire."]}
        )
    movement = StockMovement.objects.select_for_update().get(pk=movement.pk)
    if movement.cancelled_at is not None:
        raise BusinessError("invalid", "Ce mouvement est déjà annulé.")
    if movement.kind not in MANUAL_KINDS:
        raise BusinessError(
            "invalid", "Ce mouvement vient d’une réservation ou d’une maintenance : annulez-la."
        )
    item = Item.objects.select_for_update().get(pk=movement.item_id)
    if item.total_quantity - movement.delta < 0:
        raise BusinessError("invalid", "Ce stock a déjà été utilisé : impossible d’annuler.")
    item.total_quantity -= movement.delta
    item.save(update_fields=["total_quantity", "updated_at"])
    if movement.unit is not None:
        movement.unit.status = ItemUnit.Status.AVAILABLE
        movement.unit.save(update_fields=["status", "updated_at"])
    if movement.expense is not None:
        movement.expense.delete()
        movement.expense = None
    movement.cancelled_at = timezone.now()
    movement.cancel_reason = reason
    movement.cancelled_by = user
    movement.save(
        update_fields=["cancelled_at", "cancel_reason", "cancelled_by", "expense", "updated_at"]
    )
    audit.record(
        "stock.movement_cancelled",
        movement,
        request=request,
        changes={
            "item": item.name,
            "kind": movement.kind,
            "quantity": movement.quantity,
            "reason": reason,
        },
    )


# --- Maintenance --------------------------------------------------------------------------------


@transaction.atomic
def start_maintenance(
    item: Item,
    *,
    reason: str,
    user: User,
    quantity: int = 1,
    unit: ItemUnit | None = None,
    expected_end: date | None = None,
) -> Maintenance:
    item = Item.objects.select_for_update().select_related("category").get(pk=item.pk)
    if item.tracking == Item.Tracking.UNIT:
        if unit is None or unit.item_id != item.pk:
            raise BusinessError(
                "invalid", "Choisissez l’unité envoyée en maintenance.", {"unit": ["Obligatoire."]}
            )
        if unit.status not in (ItemUnit.Status.AVAILABLE, ItemUnit.Status.OUT_OF_SERVICE):
            raise BusinessError("invalid", "Cette unité n’est pas au dépôt.")
        quantity = 1
    elif quantity > _available_today(item):
        raise BusinessError(
            "stock_insufficient",
            f"Seulement {_available_today(item)} disponible(s) aujourd’hui.",
            {"quantity": ["Quantité supérieure au disponible."]},
        )
    if expected_end is not None and expected_end < today():
        raise BusinessError(
            "invalid", "Le retour prévu ne peut pas être passé.", {"expected_end": ["Date passée."]}
        )
    maintenance: Maintenance = Maintenance.objects.create(
        item=item,
        unit=unit,
        quantity=quantity,
        reason=reason.strip(),
        started_at=today(),
        expected_end=expected_end,
        created_by=user,
    )
    StockMovement.objects.create(
        item=item,
        unit=unit,
        kind=Kind.MAINTENANCE_OUT,
        quantity=quantity,
        reason=maintenance.reason,
        author=user,
        occurred_at=timezone.now(),
        created_by=user,
    )
    if unit is not None:
        unit.status = ItemUnit.Status.MAINTENANCE
        unit.save(update_fields=["status", "updated_at"])
    return maintenance


@transaction.atomic
def close_maintenance(
    maintenance: Maintenance, *, user: User, cost: int | None = None, notes: str = ""
) -> Maintenance:
    """Back from repair: available again; its cost becomes a maintenance expense (§6.1)."""
    maintenance = Maintenance.objects.select_for_update().get(pk=maintenance.pk)
    if maintenance.ended_at is not None:
        raise BusinessError("invalid", "Cette maintenance est déjà terminée.")
    maintenance.ended_at = today()
    maintenance.cost = cost
    if cost:
        maintenance.expense = _expense(
            MAINTENANCE_CATEGORY,
            label=f"Maintenance : {maintenance.item.name} ({maintenance.reason})",
            amount=cost,
            day=maintenance.ended_at,
            user=user,
        )
    maintenance.save()
    StockMovement.objects.create(
        item=maintenance.item,
        unit=maintenance.unit,
        kind=Kind.MAINTENANCE_IN,
        quantity=maintenance.quantity,
        reason=notes.strip() or maintenance.reason,
        author=user,
        occurred_at=timezone.now(),
        created_by=user,
    )
    if maintenance.unit is not None:
        maintenance.unit.status = ItemUnit.Status.AVAILABLE
        maintenance.unit.condition = ItemUnit.Condition.GOOD
        maintenance.unit.save(update_fields=["status", "condition", "updated_at"])
    return maintenance


# --- Packs --------------------------------------------------------------------------------------


@transaction.atomic
def save_pack(pack: Pack | None, data: dict[str, Any], *, user: User) -> Pack:
    components = data.pop("components", None)
    if pack is None:
        pack = Pack(created_by=user)
    for field in ("name", "description", "price", "is_active"):
        if field in data:
            setattr(pack, field, data[field])
    pack.save()
    if components is not None:
        if not components:
            raise BusinessError(
                "invalid", "Ajoutez au moins un article au pack.", {"components": ["Vide."]}
            )
        pack.components.all().delete()
        seen: set[str] = set()
        for component in components:
            key = str(component["item"].pk)
            if key in seen:
                raise BusinessError(
                    "invalid", "Un article apparaît deux fois dans le pack.", {"components": [key]}
                )
            seen.add(key)
            PackComponent.objects.create(
                pack=pack,
                item=component["item"],
                quantity=component["quantity"],
                created_by=user,
            )
    return pack


# --- Inventory ----------------------------------------------------------------------------------


@transaction.atomic
def start_inventory(*, user: User, category: ItemCategory | None = None) -> Inventory:
    """Count sheet of the quantity-tracked items (units are checked one by one in their list)."""
    inventory: Inventory = Inventory.objects.create(
        date=today(), category=category, author=user, created_by=user
    )
    items = Item.objects.filter(is_active=True, tracking=Item.Tracking.QUANTITY)
    if category is not None:
        items = items.filter(category=category)
    InventoryLine.objects.bulk_create(
        [
            InventoryLine(
                organization_id=inventory.organization_id,
                inventory=inventory,
                item=item,
                expected=item.total_quantity,
                created_by=user,
            )
            for item in items
        ]
    )
    return inventory


@transaction.atomic
def count(inventory: Inventory, counts: dict[str, int | None]) -> Inventory:
    if inventory.status != Inventory.Status.DRAFT:
        raise BusinessError("invalid", "Cet inventaire est déjà validé.")
    for line in inventory.lines.all():
        if str(line.pk) in counts:
            line.counted = counts[str(line.pk)]
            line.save(update_fields=["counted", "updated_at"])
    return inventory


@transaction.atomic
def validate_inventory(inventory: Inventory, *, user: User, request: Any) -> Inventory:
    """Every difference becomes an adjustment movement; lines left blank are not counted."""
    inventory = Inventory.objects.select_for_update().get(pk=inventory.pk)
    if inventory.status != Inventory.Status.DRAFT:
        raise BusinessError("invalid", "Cet inventaire est déjà validé.")
    adjusted = 0
    for line in inventory.lines.select_related("item"):
        difference = line.difference
        if not difference:
            continue
        record_movement(
            line.item,
            kind=Kind.ADJUSTMENT,
            quantity=abs(difference),
            direction=1 if difference > 0 else -1,
            reason=f"Inventaire du {inventory.date.strftime('%d/%m/%Y')}",
            reference=f"INV-{str(inventory.pk)[:8]}",
            user=user,
        )
        adjusted += 1
    inventory.status = Inventory.Status.VALIDATED
    inventory.validated_at = timezone.now()
    inventory.save(update_fields=["status", "validated_at", "updated_at"])
    audit.record(
        "stock.inventory_validated", inventory, request=request, changes={"adjusted": adjusted}
    )
    return inventory


# --- Reservations (checkout, return) ------------------------------------------------------------


@transaction.atomic
def reservation_movement(
    item: Item,
    *,
    kind: str,
    quantity: int,
    reference: str,
    user: User,
    reason: str = "",
) -> list[StockMovement]:
    """Movement of a reservation (checkout, return, sale, breakage, loss), under the item lock.

    The reservation already holds these quantities (checked under lock at confirmation), so no
    availability check here. Numbered equipment: the units concerned are taken in serial order.
    """
    item = Item.objects.select_for_update().get(pk=item.pk)
    delta = {Kind.SALE: -quantity, Kind.BREAKAGE: -quantity, Kind.LOSS: -quantity}.get(
        Kind(kind), 0
    )
    movements: list[StockMovement] = []
    if item.tracking == Item.Tracking.UNIT and kind in UNIT_STATUS_AFTER:
        units = list(
            item.units.filter(status=ItemUnit.Status.AVAILABLE).order_by("serial_number")[:quantity]
        )
        if len(units) < quantity:
            raise BusinessError(
                "stock_insufficient", f"Pas assez d’unités disponibles pour « {item.name} »."
            )
        for unit in units:
            unit_delta = 0 if kind == Kind.BREAKAGE else -1
            movements.append(
                StockMovement.objects.create(
                    item=item,
                    unit=unit,
                    kind=kind,
                    delta=unit_delta,
                    quantity=1,
                    reason=reason,
                    reference=reference,
                    author=user,
                    occurred_at=timezone.now(),
                    created_by=user,
                )
            )
            unit.status = UNIT_STATUS_AFTER[Kind(kind)]
            if kind == Kind.BREAKAGE:
                unit.condition = ItemUnit.Condition.DAMAGED
            unit.save(update_fields=["status", "condition", "updated_at"])
            item.total_quantity += unit_delta
    else:
        if item.total_quantity + delta < 0:
            raise BusinessError("stock_insufficient", f"Stock négatif pour « {item.name} ».")
        movements.append(
            StockMovement.objects.create(
                item=item,
                kind=kind,
                delta=delta,
                quantity=quantity,
                reason=reason,
                reference=reference,
                author=user,
                occurred_at=timezone.now(),
                created_by=user,
            )
        )
        item.total_quantity += delta
    item.save(update_fields=["total_quantity", "updated_at"])
    return movements
