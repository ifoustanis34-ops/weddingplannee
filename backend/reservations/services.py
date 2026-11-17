"""Reservation lifecycle (reservations-stock.md §4.1): draft → confirmed under lock → checkout →
return (damage billed) → closed; cancellation releases the equipment."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from accounts.models import Membership, User
from catalog.models import ServiceItem
from core import audit
from core.exceptions import BusinessError
from core.tenant import require_current_organization
from finance import invoicing as finance_invoicing
from finance import revenues as finance_revenues
from notifications import flow
from notifications.flow import MANAGERS
from organizations.models import DocumentSequence
from organizations.numbering import next_number
from organizations.timezones import org_tz
from stock import availability
from stock import services as stock_services
from stock.models import Item, Pack, StockMovement

from . import commitments
from .models import Reservation, ReservationLine, ReservationLog, ReservationPayment

Status = Reservation.Status
LineKind = ReservationLine.Kind
EQUIPMENT = (LineKind.RENTAL, LineKind.SALE, LineKind.PACK)
EDITABLE = (
    Status.DRAFT,
    Status.QUOTE_SENT,
    Status.AWAITING_DEPOSIT,
    Status.CONFIRMED,
    Status.PREPARING,
)
COMMITTED = (Status.AWAITING_DEPOSIT, Status.CONFIRMED, Status.PREPARING)
# Logistic steps that need no stock operation (checkout and return have their own actions).
TRANSITIONS: dict[str, tuple[str, ...]] = {
    Status.DRAFT: (Status.QUOTE_SENT,),
    Status.CONFIRMED: (Status.PREPARING,),
    Status.DELIVERED: (Status.INSTALLED, Status.IN_PROGRESS, Status.PICKED_UP),
    Status.INSTALLED: (Status.IN_PROGRESS, Status.PICKED_UP),
    Status.IN_PROGRESS: (Status.PICKED_UP,),
}
DATE_ORDER = (
    "delivery_at",
    "setup_at",
    "event_start",
    "event_end",
    "teardown_at",
    "pickup_at",
    "return_at",
)
DATE_LABELS = {
    "delivery_at": "la livraison",
    "setup_at": "l’installation",
    "event_start": "le début de l’événement",
    "event_end": "la fin de l’événement",
    "teardown_at": "le démontage",
    "pickup_at": "la récupération",
    "return_at": "le retour à l’entrepôt",
}
FIELDS = (
    "client",
    "wedding",
    "kind",
    "title",
    "venue",
    "address",
    "guest_count",
    "owner",
    "notes",
    "vehicle",
    "discount",
    "transport_fee",
    "setup_fee",
    *DATE_ORDER,
)


def money(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + " FCFA"


def log(reservation: Reservation, action: str, message: str, user: User | None) -> None:
    ReservationLog.objects.create(
        reservation=reservation,
        action=action,
        message=message[:255],
        author=user,
        created_by=user,
    )


# --- Lines and amounts --------------------------------------------------------------------------


@dataclass
class LineInput:
    kind: str
    quantity: int = 1
    item: Item | None = None
    pack: Pack | None = None
    service: ServiceItem | None = None
    label: str = ""
    unit_price: int | None = None
    period_days: int = 1
    deposit: int | None = None


def _line_defaults(line: LineInput) -> dict[str, Any]:
    """Label, price and caution from the source when not given."""
    if line.kind in (LineKind.RENTAL, LineKind.SALE):
        if line.item is None:
            raise BusinessError(
                "invalid", "Choisissez l’article.", {"lines": ["Article manquant."]}
            )
        if line.kind == LineKind.SALE and line.item.sale_price is None and line.unit_price is None:
            raise BusinessError(
                "invalid",
                f"« {line.item.name} » n’a pas de prix de vente.",
                {"lines": ["Article non vendu."]},
            )
        price = line.item.rent_price if line.kind == LineKind.RENTAL else line.item.sale_price
        return {
            "item": line.item,
            "label": line.label or line.item.name,
            "unit_price": line.unit_price if line.unit_price is not None else price or 0,
            "deposit": (
                line.deposit
                if line.deposit is not None
                else line.item.deposit if line.kind == LineKind.RENTAL else 0
            ),
        }
    if line.kind == LineKind.PACK:
        if line.pack is None:
            raise BusinessError("invalid", "Choisissez le pack.", {"lines": ["Pack manquant."]})
        deposit = sum(c.item.deposit * c.quantity for c in line.pack.components.all())
        return {
            "pack": line.pack,
            "label": line.label or line.pack.name,
            "unit_price": line.unit_price if line.unit_price is not None else line.pack.price,
            "deposit": line.deposit if line.deposit is not None else deposit,
        }
    if line.kind == LineKind.SERVICE:
        if line.service is None:
            raise BusinessError("invalid", "Choisissez la prestation.", {"lines": ["Manquante."]})
        return {
            "service": line.service,
            "label": line.label or line.service.name,
            "unit_price": (
                line.unit_price if line.unit_price is not None else line.service.unit_price
            ),
            "deposit": 0,
        }
    if not line.label.strip():
        raise BusinessError("invalid", "Donnez un libellé à la ligne libre.", {"lines": ["Vide."]})
    return {"label": line.label.strip(), "unit_price": line.unit_price or 0, "deposit": 0}


def line_amount(line: ReservationLine) -> int:
    days = 1
    if line.kind == LineKind.RENTAL and line.item and line.item.rent_unit == Item.RentUnit.DAY:
        days = max(1, line.period_days)
    return line.unit_price * line.quantity * days


def recompute(reservation: Reservation) -> None:
    lines = list(reservation.lines.select_related("item"))
    for line in lines:
        amount = line_amount(line)
        if amount != line.amount:
            line.amount = amount
            line.save(update_fields=["amount", "updated_at"])
    reservation.subtotal = sum(line.amount for line in lines)
    reservation.total = (
        max(0, reservation.subtotal - reservation.discount)
        + reservation.transport_fee
        + reservation.setup_fee
    )
    reservation.security_deposit = sum(line.deposit * line.quantity for line in lines)
    if reservation.deposit_required > reservation.total:
        reservation.deposit_required = reservation.total


def _replace_lines(reservation: Reservation, lines: list[LineInput], user: User) -> None:
    # Editing the lines keeps what was taken from partners, item by item (within the new
    # quantity): the editor sends lines without their partner part.
    kept = {
        str(old.item_id): (old.partner_supply_id, old.partner_quantity, old.partner_unit_cost)
        for old in reservation.lines.filter(kind=LineKind.RENTAL, partner_quantity__gt=0)
    }
    reservation.lines.exclude(kind=LineKind.DAMAGE).delete()
    for position, line in enumerate(lines):
        if line.quantity <= 0:
            raise BusinessError("invalid", "Chaque quantité doit être positive.")
        partner: dict[str, Any] = {}
        if line.kind == LineKind.RENTAL and line.item is not None and str(line.item.pk) in kept:
            supply_id, quantity, unit_cost = kept.pop(str(line.item.pk))
            partner = {
                "partner_supply_id": supply_id,
                "partner_quantity": min(quantity, line.quantity),
                "partner_unit_cost": unit_cost,
            }
        ReservationLine.objects.create(
            **partner,
            reservation=reservation,
            kind=line.kind,
            quantity=line.quantity,
            period_days=max(1, line.period_days),
            position=position,
            created_by=user,
            **_line_defaults(line),
        )


def _check_dates(data: dict[str, Any]) -> None:
    previous: tuple[str, Any] | None = None
    for name in DATE_ORDER:
        value = data.get(name)
        if value is None:
            continue
        if previous is not None and value < previous[1]:
            raise BusinessError(
                "invalid",
                f"{DATE_LABELS[name].capitalize()} doit suivre {DATE_LABELS[previous[0]]}.",
                {name: ["Date avant l’étape précédente."]},
            )
        previous = (name, value)


def _check_owner(owner: User | None) -> None:
    if (
        owner is not None
        and not Membership.objects.filter(
            user=owner, organization=require_current_organization(), is_active=True
        ).exists()
    ):
        raise BusinessError(
            "invalid", "Choisissez un membre actif de l’équipe.", {"owner": ["Hors équipe."]}
        )


def _apply(reservation: Reservation, data: dict[str, Any]) -> None:
    for name in FIELDS:
        if name in data:
            setattr(reservation, name, data[name])
    if "deposit_required" in data or "deposit_pct" in data:
        pct = data.get("deposit_pct")
        reservation.deposit_required = (
            round(reservation.total * pct / 100) if pct is not None else data["deposit_required"]
        )


@transaction.atomic
def create_reservation(data: dict[str, Any], lines: list[LineInput], *, user: User) -> Reservation:
    _check_dates({**data})
    _check_owner(data.get("owner"))
    reservation = Reservation(
        number=next_number(DocumentSequence.Kind.RESERVATION),
        created_by=user,
        owner=data.get("owner") or user,
    )
    _apply(
        reservation, {k: v for k, v in data.items() if k not in ("deposit_required", "deposit_pct")}
    )
    reservation.save()
    _replace_lines(reservation, lines, user)
    recompute(reservation)
    _apply(reservation, {k: data[k] for k in ("deposit_required", "deposit_pct") if k in data})
    recompute(reservation)
    reservation.save()
    log(reservation, "created", f"Réservation créée ({money(reservation.total)}).", user)
    flow.reservation(
        reservation, title="Nouvelle réservation", body=reservation.client.name, actor=user
    )
    return reservation


@transaction.atomic
def update_reservation(
    reservation: Reservation,
    data: dict[str, Any],
    lines: list[LineInput] | None,
    *,
    user: User,
) -> Reservation:
    reservation = Reservation.objects.select_for_update().get(pk=reservation.pk)
    if reservation.status not in EDITABLE:
        raise BusinessError(
            "reservation_locked",
            "Le matériel est déjà sorti : la réservation ne se modifie plus.",
        )
    merged = {name: data.get(name, getattr(reservation, name)) for name in DATE_ORDER}
    _check_dates(merged)
    if "owner" in data:
        _check_owner(data["owner"])
    _apply(
        reservation, {k: v for k, v in data.items() if k not in ("deposit_required", "deposit_pct")}
    )
    reservation.save()
    if lines is not None:
        _replace_lines(reservation, lines, user)
    recompute(reservation)
    _apply(reservation, {k: data[k] for k in ("deposit_required", "deposit_pct") if k in data})
    recompute(reservation)
    reservation.save()
    if reservation.status in COMMITTED:
        # New dates or quantities: the equipment must still be there (§4.3, drag in calendar).
        check_availability(reservation)
    from staff.services import follow_reservation

    follow_reservation(reservation)  # the team follows new dates (§4.3 drag, §7)
    log(reservation, "updated", "Réservation modifiée.", user)
    return reservation


@transaction.atomic
def move(reservation: Reservation, *, days: int, user: User) -> Reservation:
    """Shifts every logistic date by ``days`` (drag in the calendar, §4.3). A committed
    reservation is checked again under lock: the move is refused if the equipment is not free."""
    if days == 0:
        raise BusinessError("invalid", "Choisissez un autre jour.", {"days": ["Aucun décalage."]})
    reservation = Reservation.objects.select_for_update().get(pk=reservation.pk)
    shift = timedelta(days=days)
    data = {
        name: getattr(reservation, name) + shift
        for name in DATE_ORDER
        if getattr(reservation, name) is not None
    }
    tz = org_tz(require_current_organization())
    today = timezone.now().astimezone(tz).date()
    if timezone.localtime(data["event_start"], tz).date() < today:
        raise BusinessError(
            "invalid",
            "Une réservation ne se déplace pas dans le passé.",
            {"days": ["Date passée."]},
        )
    before = timezone.localtime(reservation.event_start, tz).date()
    reservation = update_reservation(reservation, data, None, user=user)
    after = timezone.localtime(reservation.event_start, tz).date()
    log(
        reservation,
        "moved",
        f"Déplacée du {before:%d/%m/%Y} au {after:%d/%m/%Y}.",
        user,
    )
    return reservation


# --- Availability (§5.2) ------------------------------------------------------------------------


@dataclass
class Shortage:
    item: Item
    needed: int
    available: int
    alternatives: list[dict[str, Any]] = field(default_factory=list)


def needs(reservation: Reservation) -> dict[str, int]:
    """Quantity of each item the reservation takes (packs expanded)."""
    totals: dict[str, int] = defaultdict(int)
    for line in reservation.lines.filter(kind__in=EQUIPMENT).prefetch_related("pack__components"):
        if line.kind == LineKind.PACK and line.pack is not None:
            for component in line.pack.components.all():
                totals[str(component.item_id)] += component.quantity * line.quantity
        elif line.item_id is not None:
            # A partner's part never comes out of our stock (feedback 14/11/2026).
            own = line.quantity - line.partner_quantity
            if own > 0:
                totals[str(line.item_id)] += own
    return totals


def period(reservation: Reservation) -> tuple[date, date]:
    tz = org_tz(require_current_organization())
    today = timezone.now().astimezone(tz).date()
    return commitments.window(reservation, tz, today)


def shortages(reservation: Reservation, *, lock: bool = False) -> list[Shortage]:
    """Items the reservation asks more of than what is free over its period (itself excluded)."""
    wanted = needs(reservation)
    if not wanted:
        return []
    query = availability.lock_items(wanted) if lock else Item.objects.filter(pk__in=list(wanted))
    items = {str(i.pk): i for i in query.select_related("category")}
    first, last = period(reservation)
    today = timezone.localdate()
    values = availability.compute(
        items.values(), first, last, today, exclude_reservation=str(reservation.pk)
    )
    found = []
    for item_id, needed in wanted.items():
        free = values[item_id].available
        if needed > free:
            found.append(Shortage(items[item_id], needed, free))
    return found


def alternatives(shortage: Shortage, first: date, last: date) -> list[dict[str, Any]]:
    """Equivalent items (same category) free over the period: suggested in place (§4.2)."""
    others = list(
        Item.objects.filter(category=shortage.item.category, is_active=True)
        .exclude(pk=shortage.item.pk)
        .select_related("category")
    )
    values = availability.compute(others, first, last, timezone.localdate())
    return [
        {"item": str(o.pk), "name": o.name, "available": values[str(o.pk)].available}
        for o in others
        if values[str(o.pk)].available > 0
    ][:3]


def check_availability(reservation: Reservation) -> None:
    """Under row locks (same order everywhere): two confirmations can never exceed the stock,
    nor what a partner can lend."""
    from . import partners

    partners.check(reservation)
    missing = shortages(reservation, lock=True)
    if missing:
        details = "; ".join(
            f"{s.item.name} : {s.needed} demandés, {s.available} disponibles" for s in missing
        )
        raise BusinessError(
            "stock_insufficient",
            f"Stock insuffisant sur la période — {details}.",
            {
                "lines": [
                    f"{s.item.name} : {s.needed} demandés, {s.available} disponibles"
                    for s in missing
                ]
            },
        )


# --- Lifecycle ----------------------------------------------------------------------------------


def paid(reservation: Reservation) -> int:
    total = reservation.payments.filter(
        kind=ReservationPayment.Kind.PAYMENT, is_cancelled=False
    ).aggregate(total=Sum("amount"))["total"]
    return int(total or 0)


@transaction.atomic
def confirm(reservation: Reservation, *, user: User) -> Reservation:
    """Stock checked under lock; confirmed once the deposit is paid, else awaiting it."""
    reservation = Reservation.objects.select_for_update().get(pk=reservation.pk)
    if reservation.status not in (Status.DRAFT, Status.QUOTE_SENT):
        raise BusinessError("invalid", "Cette réservation est déjà confirmée ou close.")
    if not reservation.lines.exists():
        raise BusinessError("invalid", "Ajoutez au moins une ligne avant de confirmer.")
    check_availability(reservation)
    reservation.confirmed_at = timezone.now()
    reservation.status = (
        Status.CONFIRMED
        if paid(reservation) >= reservation.deposit_required
        else Status.AWAITING_DEPOSIT
    )
    reservation.save(update_fields=["status", "confirmed_at", "updated_at"])
    log(
        reservation,
        "confirmed",
        (
            "Réservation confirmée : matériel bloqué."
            if reservation.status == Status.CONFIRMED
            else "Matériel bloqué, en attente de l’acompte "
            f"({money(reservation.deposit_required)})."
        ),
        user,
    )
    flow.reservation(
        reservation,
        title=(
            "Réservation confirmée"
            if reservation.status == Status.CONFIRMED
            else "Réservation en attente d’acompte"
        ),
        body="matériel bloqué",
        actor=user,
        roles=("owner", "planner", "storekeeper"),
    )
    return reservation


@transaction.atomic
def advance(reservation: Reservation, status: str, *, user: User) -> Reservation:
    reservation = Reservation.objects.select_for_update().get(pk=reservation.pk)
    allowed = TRANSITIONS.get(reservation.status, ())
    has_equipment = reservation.lines.filter(kind__in=EQUIPMENT).exists()
    if not has_equipment and reservation.status in (Status.CONFIRMED, Status.PREPARING):
        allowed = (*allowed, Status.IN_PROGRESS)  # services only: no checkout
    if not has_equipment and reservation.status == Status.IN_PROGRESS:
        allowed = (*allowed, Status.CLOSED)
    if status not in allowed:
        raise BusinessError(
            "invalid",
            f"Impossible de passer de « {Status(reservation.status).label} » "
            f"à « {Status(status).label} ».",
        )
    reservation.status = status
    if status == Status.CLOSED:
        reservation.returned_at = timezone.now()
    reservation.save(update_fields=["status", "returned_at", "updated_at"])
    log(reservation, "status", f"Étape : {Status(status).label}.", user)
    flow.reservation(
        reservation,
        title=f"Réservation : {Status(status).label.lower()}",
        actor=user,
        roles=("owner", "planner", "storekeeper") if status == Status.PREPARING else MANAGERS,
    )
    return reservation


@transaction.atomic
def checkout(
    reservation: Reservation, quantities: dict[str, int] | None, *, user: User
) -> Reservation:
    """« Bon de sortie » (§4.1): the equipment leaves; sales leave the stock for good."""
    reservation = Reservation.objects.select_for_update().get(pk=reservation.pk)
    if reservation.status not in (Status.CONFIRMED, Status.PREPARING):
        raise BusinessError(
            "invalid",
            "Seule une réservation confirmée (acompte reçu) sort de l’entrepôt.",
        )
    quantities = quantities or {}
    for line in reservation.lines.filter(kind__in=EQUIPMENT).select_related("item", "pack"):
        own = line.quantity - line.partner_quantity  # the partner delivers its own part
        out = quantities.get(str(line.pk), own)
        if not 0 <= out <= own:
            raise BusinessError(
                "invalid",
                f"« {line.label} » : entre 0 et {own}.",
                {"lines": [str(line.pk)]},
            )
        line.quantity_out = out
        line.save(update_fields=["quantity_out", "updated_at"])
        if not out:
            continue
        kind = (
            StockMovement.Kind.SALE if line.kind == LineKind.SALE else StockMovement.Kind.CHECKOUT
        )
        for item, quantity in _items_of(line, out):
            stock_services.reservation_movement(
                item,
                kind=kind,
                quantity=quantity,
                reference=reservation.number,
                reason=reservation.title,
                user=user,
            )
    reservation.status = Status.DELIVERED
    reservation.checked_out_at = timezone.now()
    reservation.save(update_fields=["status", "checked_out_at", "updated_at"])
    log(reservation, "checkout", "Matériel sorti de l’entrepôt (bon de sortie).", user)
    flow.reservation(
        reservation,
        title="Matériel sorti de l’entrepôt",
        actor=user,
        roles=("owner", "planner", "storekeeper"),
    )
    return reservation


def _items_of(line: ReservationLine, quantity: int) -> list[tuple[Item, int]]:
    if line.kind == LineKind.PACK and line.pack is not None:
        return [
            (c.item, c.quantity * quantity) for c in line.pack.components.select_related("item")
        ]
    assert line.item is not None
    return [(line.item, quantity)]


@dataclass
class ReturnInput:
    returned: int
    damaged: int = 0
    missing: int = 0


@transaction.atomic
def process_return(
    reservation: Reservation, counts: dict[str, ReturnInput], *, user: User
) -> Reservation:
    """« Bon de retour » (§4.1): what came back, damaged or missing. Damage and losses become
    stock movements and a billable « Casse et pertes » line at the replacement price."""
    reservation = Reservation.objects.select_for_update().get(pk=reservation.pk)
    if reservation.status not in commitments.OUT:
        raise BusinessError("invalid", "Rien n’est sorti pour cette réservation.")
    position = reservation.lines.count()
    for line in reservation.lines.filter(kind__in=(LineKind.RENTAL, LineKind.PACK)).select_related(
        "item", "pack"
    ):
        if not line.quantity_out:
            continue
        count = counts.get(str(line.pk), ReturnInput(returned=line.quantity_out))
        if min(count.returned, count.damaged, count.missing) < 0 or (
            count.returned + count.damaged + count.missing != line.quantity_out
        ):
            raise BusinessError(
                "invalid",
                f"« {line.label} » : {line.quantity_out} sortis, comptez chaque pièce "
                "(rendue, abîmée ou manquante).",
                {"lines": [str(line.pk)]},
            )
        if line.kind == LineKind.PACK and (count.damaged or count.missing):
            raise BusinessError(
                "invalid",
                f"« {line.label} » : saisissez la casse d’un pack sur ses articles.",
                {"lines": [str(line.pk)]},
            )
        line.quantity_returned = count.returned
        line.quantity_damaged = count.damaged
        line.quantity_missing = count.missing
        line.save(
            update_fields=[
                "quantity_returned",
                "quantity_damaged",
                "quantity_missing",
                "updated_at",
            ]
        )
        for item, quantity in _items_of(line, count.returned):
            stock_services.reservation_movement(
                item,
                kind=StockMovement.Kind.RETURN,
                quantity=quantity,
                reference=reservation.number,
                reason=reservation.title,
                user=user,
            )
        if line.item is None:
            continue
        for kind, quantity in (
            (StockMovement.Kind.BREAKAGE, count.damaged),
            (StockMovement.Kind.LOSS, count.missing),
        ):
            if quantity:
                stock_services.reservation_movement(
                    line.item,
                    kind=kind,
                    quantity=quantity,
                    reference=reservation.number,
                    reason=f"Retour {reservation.number}",
                    user=user,
                )
        lost = count.damaged + count.missing
        if lost:
            price = line.item.sale_price or line.item.purchase_cost
            parts = []
            if count.damaged:
                parts.append(f"{count.damaged} abîmé(s)")
            if count.missing:
                parts.append(f"{count.missing} manquant(s)")
            ReservationLine.objects.create(
                reservation=reservation,
                kind=LineKind.DAMAGE,
                item=line.item,
                label=f"Casse et pertes : {line.item.name} ({', '.join(parts)})",
                quantity=lost,
                unit_price=price,
                amount=price * lost,
                position=position,
                created_by=user,
            )
            position += 1
    recompute(reservation)
    reservation.status = Status.CLOSED
    reservation.returned_at = timezone.now()
    reservation.save()
    damage = reservation.lines.filter(kind=LineKind.DAMAGE).aggregate(t=Sum("amount"))["t"] or 0
    log(
        reservation,
        "return",
        "Retour saisi (bon de retour)"
        + (f" ; casse et pertes facturées : {money(int(damage))}." if damage else "."),
        user,
    )
    flow.reservation(
        reservation,
        title="Matériel rentré" + (" avec casse ou pertes" if damage else ""),
        body="casse et pertes à facturer" if damage else "",
        actor=user,
        roles=("owner", "planner", "storekeeper"),
    )
    return reservation


@transaction.atomic
def cancel(reservation: Reservation, *, reason: str, user: User, request: Any) -> Reservation:
    """Releases the equipment; the deposit follows the agency's policy (Paramètres)."""
    reservation = Reservation.objects.select_for_update().get(pk=reservation.pk)
    if reservation.status in commitments.OUT or reservation.status in (
        Status.CLOSED,
        Status.CANCELLED,
    ):
        raise BusinessError(
            "invalid", "Le matériel est sorti ou la réservation est close : annulation impossible."
        )
    reason = reason.strip()
    if not reason:
        raise BusinessError(
            "invalid", "Indiquez le motif de l’annulation.", {"reason": ["Obligatoire."]}
        )
    received = paid(reservation)
    kept = reservation.deposit_required if reservation.organization.deposit_kept_on_cancel else 0
    reservation.refund_due = max(0, received - kept)
    reservation.status = Status.CANCELLED
    reservation.cancelled_at = timezone.now()
    reservation.cancel_reason = reason
    reservation.save()
    # §6.3: credit notes for what the client no longer owes (the kept deposit stays invoiced).
    finance_invoicing.on_reservation_cancelled(reservation, kept=min(kept, received), user=user)
    log(
        reservation,
        "cancelled",
        f"Annulée : {reason}"
        + (
            f" ; à rembourser : {money(reservation.refund_due)}." if reservation.refund_due else "."
        ),
        user,
    )
    audit.record(
        "reservation.cancelled",
        reservation,
        request=request,
        changes={"reason": reason, "refund_due": reservation.refund_due},
    )
    flow.reservation(
        reservation,
        title="Réservation annulée",
        body=reason.strip()[:120],
        actor=user,
        roles=("owner", "planner", "storekeeper", "accountant"),
    )
    return reservation


# --- Payments and security deposit --------------------------------------------------------------


@transaction.atomic
def record_payment(
    reservation: Reservation,
    *,
    amount: int,
    method: str,
    paid_at: date,
    user: User,
    reference: str = "",
    kind: str = ReservationPayment.Kind.PAYMENT,
    request: Any = None,
) -> ReservationPayment:
    reservation = Reservation.objects.select_for_update().get(pk=reservation.pk)
    if reservation.status in (Status.DRAFT, Status.CANCELLED):
        raise BusinessError("invalid", "Confirmez la réservation avant d’encaisser.")
    if paid_at > timezone.localdate():
        raise BusinessError("invalid", "La date ne peut pas être future.", {"paid_at": ["Future."]})
    if amount <= 0:
        raise BusinessError("invalid", "Montant positif.", {"amount": ["> 0"]})
    if kind == ReservationPayment.Kind.PAYMENT:
        balance = reservation.total - paid(reservation)
        if amount > balance:
            raise BusinessError(
                "payment_exceeds_balance",
                f"Le montant dépasse le solde restant ({money(balance)}).",
                {"amount": [f"Maximum {balance:,}".replace(",", " ")]},
            )
    elif kind == ReservationPayment.Kind.SECURITY:
        if reservation.security_status != Reservation.SecurityStatus.NONE:
            raise BusinessError("invalid", "La caution est déjà encaissée.")
        reservation.security_status = Reservation.SecurityStatus.HELD
    payment: ReservationPayment = ReservationPayment.objects.create(
        reservation=reservation,
        kind=kind,
        amount=amount,
        method=method,
        paid_at=paid_at,
        reference=reference.strip(),
        recorded_by=user,
        created_by=user,
    )
    if (
        reservation.status == Status.AWAITING_DEPOSIT
        and paid(reservation) >= reservation.deposit_required
    ):
        reservation.status = Status.CONFIRMED
        log(reservation, "confirmed", "Acompte reçu : réservation confirmée.", user)
    reservation.save()
    log(reservation, "payment", f"{payment.get_kind_display()} : {money(amount)}.", user)
    finance_revenues.record_reservation_payment(payment)  # §6.1: the revenue, by category
    audit.record(
        "reservation.payment",
        reservation,
        request=request,
        changes={"amount": amount, "kind": kind, "method": method},
    )
    if kind == ReservationPayment.Kind.PAYMENT:
        from notifications import push

        push.notify(
            push.members_with_roles(["owner", "accountant"], exclude=user.pk),
            title="Paiement reçu",
            body=f"{money(amount)} · {reservation.number} · {reservation.client.name}",
            url=f"/reservations?reservation={reservation.pk}",
            kind="payment",
            tag=f"payment-{payment.pk}",
        )
    return payment


@transaction.atomic
def settle_security(
    reservation: Reservation, *, retained: int, method: str, user: User, reason: str = ""
) -> Reservation:
    """Caution back to the client, minus what the agency keeps (damage not billed otherwise)."""
    reservation = Reservation.objects.select_for_update().get(pk=reservation.pk)
    if reservation.security_status != Reservation.SecurityStatus.HELD:
        raise BusinessError("invalid", "Aucune caution encaissée à restituer.")
    held = int(
        reservation.payments.filter(
            kind=ReservationPayment.Kind.SECURITY, is_cancelled=False
        ).aggregate(t=Sum("amount"))["t"]
        or 0
    )
    if not 0 <= retained <= held:
        raise BusinessError(
            "invalid", f"Retenue entre 0 et {money(held)}.", {"retained": ["Hors limites."]}
        )
    if held - retained:
        ReservationPayment.objects.create(
            reservation=reservation,
            kind=ReservationPayment.Kind.SECURITY_REFUND,
            amount=held - retained,
            method=method,
            paid_at=timezone.localdate(),
            reference=reason[:80],
            recorded_by=user,
            created_by=user,
        )
    reservation.security_retained = retained
    reservation.security_status = (
        Reservation.SecurityStatus.RETAINED if retained else Reservation.SecurityStatus.REFUNDED
    )
    reservation.save(update_fields=["security_retained", "security_status", "updated_at"])
    log(
        reservation,
        "security",
        f"Caution : {money(held - retained)} restitués"
        + (f", {money(retained)} retenus ({reason})." if retained else "."),
        user,
    )
    return reservation


@transaction.atomic
def cancel_payment(
    payment: ReservationPayment, *, reason: str, user: User, request: Any
) -> ReservationPayment:
    """Never deleted (§12): cancelled with a reason, traced."""
    payment = ReservationPayment.objects.select_for_update().get(pk=payment.pk)
    if payment.is_cancelled:
        raise BusinessError("invalid", "Ce paiement est déjà annulé.")
    if not reason.strip():
        raise BusinessError("invalid", "Indiquez le motif.", {"reason": ["Obligatoire."]})
    payment.is_cancelled = True
    payment.cancelled_at = timezone.now()
    payment.cancel_reason = reason.strip()
    payment.save(update_fields=["is_cancelled", "cancelled_at", "cancel_reason", "updated_at"])
    reservation = payment.reservation
    if payment.kind == ReservationPayment.Kind.SECURITY:
        reservation.security_status = Reservation.SecurityStatus.NONE
        reservation.save(update_fields=["security_status", "updated_at"])
    log(reservation, "payment_cancelled", f"Paiement annulé : {reason}", user)
    finance_revenues.cancel_for_reservation_payment(payment)
    audit.record(
        "reservation.payment_cancelled",
        payment,
        request=request,
        changes={"amount": payment.amount, "reason": reason},
    )
    return payment


def next_step(reservation: Reservation, today: date | None = None) -> dict[str, Any] | None:
    """Next logistic step shown in the list (« Livraison le 14 nov. »)."""
    steps = {
        Status.AWAITING_DEPOSIT: ("deposit", None),
        Status.CONFIRMED: ("delivery", reservation.delivery_at or reservation.event_start),
        Status.PREPARING: ("delivery", reservation.delivery_at or reservation.event_start),
        Status.DELIVERED: ("setup", reservation.setup_at or reservation.event_start),
        Status.INSTALLED: ("event", reservation.event_start),
        Status.IN_PROGRESS: ("pickup", reservation.pickup_at or reservation.event_end),
        Status.PICKED_UP: ("return", reservation.return_at or reservation.pickup_at),
    }
    if reservation.status not in steps:
        return None
    key, when = steps[Status(reservation.status)]
    return {"key": key, "at": when}


__all__ = [
    "LineInput",
    "ReturnInput",
    "advance",
    "cancel",
    "checkout",
    "confirm",
    "create_reservation",
    "process_return",
    "record_payment",
]
