"""Equipment lent by partners (feedback 14/11/2026).

A rental line can take part of its quantity from a partner (``stock.PartnerSupply``): our own
stock only gives ``quantity - partner_quantity``. A partner lends at most ``supply.quantity``
units on any day: committed reservations overlapping the period share that capacity.

    free(supply, period) = supply.quantity − partner quantities of overlapping committed
                           reservations, on the busiest day of the period.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any

from django.db import transaction
from django.utils import timezone

from accounts.models import User
from core.exceptions import BusinessError
from core.tenant import require_current_organization
from organizations.timezones import org_tz
from stock.models import Item, PartnerSupply

from . import commitments
from .models import Reservation, ReservationLine

LineKind = ReservationLine.Kind
Status = Reservation.Status
# Until the equipment leaves: afterwards the partner part is what was agreed.
EDITABLE = (
    Status.DRAFT,
    Status.QUOTE_SENT,
    Status.AWAITING_DEPOSIT,
    Status.CONFIRMED,
    Status.PREPARING,
)


@dataclass(frozen=True)
class Offer:
    supply: PartnerSupply
    free: int


def _today() -> date:
    return timezone.now().astimezone(org_tz(require_current_organization())).date()


def committed(
    supply_ids: list[str], first: date, last: date, *, exclude: str | None = None
) -> dict[str, int]:
    """Partner units already promised, per supply, on the busiest day of [first, last]."""
    tz = org_tz(require_current_organization())
    today = _today()
    lines = ReservationLine.objects.filter(
        partner_supply_id__in=supply_ids,
        partner_quantity__gt=0,
        reservation__status__in=commitments.RESERVED + commitments.OUT,
    ).select_related("reservation")
    if exclude:
        lines = lines.exclude(reservation_id=exclude)
    spans: dict[str, list[tuple[date, date, int]]] = defaultdict(list)
    for line in lines:
        start, end = commitments.window(line.reservation, tz, today)
        if end < first or start > last:
            continue
        spans[str(line.partner_supply_id)].append((start, end, line.partner_quantity))
    peaks: dict[str, int] = {}
    for supply_id, found in spans.items():
        days = {first} | {s for s, _, _ in found if first <= s <= last}
        peaks[supply_id] = max(sum(q for s, e, q in found if s <= day <= e) for day in sorted(days))
    return peaks


def offers(item: Item, first: date, last: date, *, exclude: str | None = None) -> list[Offer]:
    """Active partners lending this item, with what they can still lend over the period."""
    supplies = list(
        PartnerSupply.objects.filter(
            item=item, is_active=True, quantity__gt=0, vendor__is_deleted=False
        ).select_related("vendor", "item")
    )
    taken = committed([str(s.pk) for s in supplies], first, last, exclude=exclude)
    return [Offer(s, max(0, s.quantity - taken.get(str(s.pk), 0))) for s in supplies]


def free(supply: PartnerSupply, reservation: Reservation) -> int:
    first, last = commitments.window(reservation, org_tz(require_current_organization()), _today())
    taken = committed([str(supply.pk)], first, last, exclude=str(reservation.pk))
    return max(0, supply.quantity - taken.get(str(supply.pk), 0))


@transaction.atomic
def assign(
    reservation: Reservation,
    line: ReservationLine,
    supply: PartnerSupply | None,
    quantity: int,
    *,
    user: User,
) -> ReservationLine:
    """Take ``quantity`` units of a rental line from a partner (0 or no supply: all ours)."""
    from .services import log

    reservation = Reservation.objects.select_for_update().get(pk=reservation.pk)
    if reservation.status not in EDITABLE:
        raise BusinessError(
            "invalid", "Le matériel est déjà sorti : la part du partenaire ne change plus."
        )
    if line.reservation_id != reservation.pk or line.kind != LineKind.RENTAL or not line.item_id:
        raise BusinessError(
            "invalid", "Seule une ligne de location d’un article se complète chez un partenaire."
        )
    if quantity < 0 or quantity > line.quantity:
        raise BusinessError(
            "invalid",
            f"Entre 0 et {line.quantity} pour « {line.label} ».",
            {"quantity": ["Quantité hors limites."]},
        )
    if supply is None or quantity == 0:
        line.partner_supply, line.partner_quantity, line.partner_unit_cost = None, 0, 0
        line.save(
            update_fields=["partner_supply", "partner_quantity", "partner_unit_cost", "updated_at"]
        )
        log(reservation, "partner", f"« {line.label} » : tout vient de notre stock.", user)
        return line
    supply = PartnerSupply.objects.select_for_update().select_related("vendor").get(pk=supply.pk)
    if supply.item_id != line.item_id or not supply.is_active:
        raise BusinessError(
            "invalid", "Ce partenaire ne prête pas cet article.", {"supply": ["Mauvais article."]}
        )
    available = free(supply, reservation)
    if quantity > available:
        raise BusinessError(
            "partner_insufficient",
            f"{supply.vendor.name} peut encore prêter {available} « {line.label} » "
            "sur cette période.",
            {"quantity": [f"{available} au plus."]},
        )
    line.partner_supply = supply
    line.partner_quantity = quantity
    line.partner_unit_cost = supply.unit_cost
    line.save(
        update_fields=["partner_supply", "partner_quantity", "partner_unit_cost", "updated_at"]
    )
    log(
        reservation,
        "partner",
        f"« {line.label} » : {quantity} chez {supply.vendor.name}, "
        f"{line.quantity - quantity} de notre stock.",
        user,
    )
    return line


def check(reservation: Reservation) -> None:
    """At confirmation, under lock: every partner part still fits the partner's capacity."""
    lines = list(
        reservation.lines.filter(partner_quantity__gt=0, partner_supply__isnull=False)
        .select_related("partner_supply__vendor", "item")
        .order_by("partner_supply_id")
    )
    if not lines:
        return
    ids = sorted({str(line.partner_supply_id) for line in lines})
    list(PartnerSupply.objects.select_for_update().filter(pk__in=ids).order_by("pk"))
    wanted: dict[str, int] = defaultdict(int)
    for line in lines:
        wanted[str(line.partner_supply_id)] += line.partner_quantity
    problems = []
    for line in {str(line.partner_supply_id): line for line in lines}.values():
        supply = line.partner_supply
        assert supply is not None
        can = free(supply, reservation)
        if wanted[str(supply.pk)] > can or not supply.is_active:
            problems.append(
                f"{supply.vendor.name} : {wanted[str(supply.pk)]} « {line.label} » "
                f"demandés, {can if supply.is_active else 0} disponibles"
            )
    if problems:
        raise BusinessError(
            "partner_insufficient",
            "Matériel partenaire insuffisant sur la période — " + "; ".join(problems) + ".",
            {"lines": problems},
        )


def cost(reservation: Reservation) -> int:
    """What the partners charge for this reservation (a direct cost, §6.4)."""
    return sum(
        line.partner_quantity * line.partner_unit_cost
        for line in reservation.lines.filter(partner_quantity__gt=0)
    )


def orders(reservation: Reservation) -> list[dict[str, Any]]:
    """One order per partner: what to ask for, how much it costs."""
    grouped: dict[str, dict[str, Any]] = {}
    for line in (
        reservation.lines.filter(partner_quantity__gt=0, partner_supply__isnull=False)
        .select_related("partner_supply__vendor", "item")
        .order_by("position")
    ):
        supply = line.partner_supply
        assert supply is not None
        vendor = supply.vendor
        order = grouped.setdefault(
            str(vendor.pk),
            {
                "vendor": str(vendor.pk),
                "vendor_name": vendor.name,
                "contact": vendor.contact_name,
                "phone": vendor.phone or vendor.whatsapp,
                "lines": [],
                "total": 0,
            },
        )
        total = line.partner_quantity * line.partner_unit_cost
        order["lines"].append(
            {
                "line": str(line.pk),
                "label": line.label,
                "reference": line.item.reference if line.item else "",
                "quantity": line.partner_quantity,
                "unit_cost": line.partner_unit_cost,
                "total": total,
            }
        )
        order["total"] += total
    return list(grouped.values())
