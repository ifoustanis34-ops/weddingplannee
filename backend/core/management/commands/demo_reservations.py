"""Reservations of the demo agency (reservations-stock.md §11): over six weeks around today,
12 reservations — 2 closed (one with 6 broken glasses and 2 missing covers billed), 1 picked up
and late, 1 in progress today, 1 installed, 2 in preparation (delivery in 1 and 3 days), 3
confirmed, 1 awaiting its deposit (280 Chiavari chairs for 250: stock alert), 1 cancelled with
its credit note. 5 complete weddings linked to their wedding record, 4 rentals, 2 sales, 1
mixed."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any

from django.utils import timezone

from accounts.models import User
from crm.models import Client
from events.models import Wedding
from finance import invoicing as finance_invoicing
from finance.models import Invoice
from reservations import services
from reservations.models import Reservation, ReservationPayment
from stock.models import Item, Pack

Status = Reservation.Status
MARKER = "Baptême du petit Emmanuel"


@dataclass
class Demo:
    title: str
    client: str
    kind: str
    day: int  # event start, days from today
    status: str
    lines: list[tuple[str, str, int]]  # kind, item or pack name or label, quantity
    venue: str = ""
    days: int = 1
    paid: float = 0.0  # share of the total collected
    deposit: float = 0.3
    wedding: str | None = None
    fees: tuple[int, int] = (0, 0)  # transport, setup
    returned: dict[str, tuple[int, int]] = field(default_factory=dict)  # damaged, missing
    services_: list[tuple[str, int]] = field(default_factory=list)  # free lines (label, price)
    lead: int = 1  # delivery, days before the event
    oversold: bool = False  # booked beyond the stock: the « stock insuffisant » alert (§11)


DEMOS = [
    Demo(
        MARKER,
        "Paroisse Saint-Joseph",
        "rental",
        -18,
        Status.CLOSED,
        [
            ("rental", "Chaise Napoléon dorée", 80),
            ("rental", "Table ronde 10 personnes", 8),
            ("rental", "Nappe ronde blanche", 8),
            ("rental", "Verre à pied", 160),
            ("rental", "Housse de chaise lycra", 80),
        ],
        venue="Paroisse Saint-Joseph, Akwa, Douala",
        paid=1.0,
        fees=(25_000, 0),
        returned={"Verre à pied": (6, 0), "Housse de chaise lycra": (0, 2)},
    ),
    Demo(
        "Achat de nappes et chandeliers",
        "Agence Lumière Douala",
        "sale",
        -12,
        Status.CLOSED,
        [("sale", "Nappe ronde blanche", 20), ("sale", "Chandelier 5 branches", 10)],
        venue="Livraison à Douala",
        paid=1.0,
        fees=(45_000, 0),
    ),
    Demo(
        "Dot de la famille Ekotto",
        "Famille Ekotto",
        "rental",
        -3,
        Status.PICKED_UP,
        [
            ("rental", "Tente pagode 5 × 5 m", 2),
            ("rental", "Chaise Napoléon dorée", 60),
            ("rental", "Guirlande guinguette 20 m", 4),
        ],
        venue="Domaine Ekotto, Yaoundé",
        paid=0.5,
        fees=(60_000, 20_000),
    ),
    Demo(
        "Séminaire annuel Orange Events",
        "Société Orange Events",
        "rental",
        0,
        Status.IN_PROGRESS,
        [
            ("rental", "Chaise Napoléon dorée", 120),
            ("rental", "Table rectangulaire 2 m", 20),
            ("rental", "Sono complète 2 × 1000 W", 1),
            ("rental", "Projecteur LED", 4),
            ("rental", "Verre à pied", 250),
        ],
        venue="Hôtel Sawa, Douala",
        paid=0.6,
        fees=(30_000, 40_000),
        services_=[("Coordination technique de la journée", 150_000)],
    ),
    Demo(
        "Mariage coutumier Diabaté",
        "Famille Diabaté",
        "mixed",
        1,
        Status.INSTALLED,
        [
            ("rental", "Arche florale ronde", 1),
            ("rental", "Chaise Napoléon dorée", 100),
            ("rental", "Centre de table fleurs artificielles", 10),
            ("rental", "Verre à pied", 200),
        ],
        venue="Jardins de Bonamoussadi, Douala",
        paid=0.5,
        fees=(35_000, 50_000),
        services_=[("Décoration florale sur mesure", 400_000)],
        wedding="Famille Diabaté",
    ),
    Demo(
        "Mariage Mariam & Idriss",
        "Mariam & Idriss",
        "mixed",
        3,
        Status.PREPARING,
        [
            ("pack", "Pack réception 250 invités", 1),
            ("pack", "Pack cérémonie", 1),
            ("pack", "Pack lumière & son", 1),
        ],
        venue="Salle Bellevue, Bonapriso",
        days=1,
        paid=0.3,
        fees=(80_000, 120_000),
        wedding="Mariam & Idriss",
        lead=2,  # delivery in 1 day, the other preparation in 3 (§11)
        services_=[("Coordination complète du mariage", 650_000)],
    ),
    Demo(
        "Anniversaire de Mme Ngo Bassong",
        "Mme Ngo Bassong",
        "rental",
        4,
        Status.PREPARING,
        [
            ("rental", "Table ronde 10 personnes", 6),
            ("rental", "Guirlande guinguette 20 m", 5),
            ("rental", "Canapé VIP blanc", 2),
        ],
        venue="Résidence Bassong, Bonapriso",
        paid=0.3,
        fees=(15_000, 10_000),
    ),
    Demo(
        "Achat de chandeliers et chemins de table",
        "Agence Lumière Douala",
        "sale",
        9,
        Status.CONFIRMED,
        [
            ("sale", "Chandelier 5 branches", 10),
            ("sale", "Chemin de table doré", 40),
        ],
        venue="Livraison à Douala",
        paid=0.3,
        fees=(30_000, 0),
    ),
    Demo(
        "Mariage Famille Kouamé",
        "Famille Kouamé",
        "mixed",
        14,
        Status.CONFIRMED,
        [
            ("pack", "Pack réception 100 invités", 2),
            ("rental", "Table d’honneur modulable", 2),
            ("rental", "Chapiteau 10 × 20 m", 1),
        ],
        venue="Espace Diamant, Bastos, Yaoundé",
        paid=0.3,
        fees=(60_000, 150_000),
        services_=[
            ("Coordination complète du mariage", 1_200_000),
            ("Décoration florale de la salle", 900_000),
        ],
        wedding="Famille Kouamé",
    ),
    Demo(
        "Mariage Famille Ekotto",
        "Famille Ekotto",
        "mixed",
        20,
        Status.CONFIRMED,
        [
            ("pack", "Pack réception 100 invités", 1),
            ("pack", "Pack lumière & son", 1),
            ("rental", "Groupe électrogène 20 kVA", 1),
        ],
        venue="Domaine Ekotto, Yaoundé",
        paid=0.3,
        fees=(250_000, 80_000),
        wedding="Famille Ekotto",
        services_=[("Coordination le jour J", 250_000)],
    ),
    Demo(
        "Fiançailles Tchouta",
        "Famille Tchouta",
        "mixed",
        11,
        Status.CANCELLED,
        [("rental", "Chaise Napoléon dorée", 50), ("rental", "Tente pagode 5 × 5 m", 1)],
        venue="Douala, Bonamoussadi",
        paid=0.3,
        fees=(20_000, 0),
        services_=[("Décoration florale", 150_000)],
    ),
    Demo(
        "Mariage Grâce & Yannick — réception 280 invités",
        "Grâce & Yannick",
        "mixed",
        19,
        Status.AWAITING_DEPOSIT,
        [
            ("rental", "Chaise Chiavari transparente", 280),
            ("rental", "Table ronde 10 personnes", 28),
            ("rental", "Nappe ronde blanche", 28),
        ],
        venue="Hilton, Yaoundé",
        fees=(90_000, 120_000),
        services_=[("Coordination complète du mariage", 900_000)],
        wedding="Grâce & Yannick",
        oversold=True,
    ),
]


# The agency's fleet (§4.3: the vehicle shows in the logistic planning).
VEHICLES = (
    "Camion 3,5 t · 4512 HK 01",
    "Fourgon Master · 2208 GH 01",
    "Pick-up Hilux · 7734 JB 01",
)


def _at(day: int, hour: int) -> datetime:
    return timezone.make_aware(
        datetime.combine(timezone.localdate() + timedelta(days=day), time(hour))
    )


def _client(name: str, owner: User) -> Client:
    client: Client | None = Client.objects.filter(name=name).first()
    if client is None:
        client = Client.objects.create(name=name, created_by=owner)
    if client.is_archived:
        client.is_archived = False
        client.save(update_fields=["is_archived", "updated_at"])
    return client


def _wedding(demo: Demo, owner: User) -> Wedding:
    """The wedding record of a complete wedding (§11), created when missing."""
    found: Wedding | None = (
        Wedding.objects.filter(client__name=demo.wedding).order_by("-date").first()
    )
    if found is None:
        found = Wedding.objects.create(
            title=demo.wedding or demo.title,
            date=timezone.localdate() + timedelta(days=demo.day),
            venue=demo.venue,
            client=_client(demo.client, owner),
            created_by=owner,
        )
    return found


def _past(day: int) -> date:
    return min(timezone.localdate(), timezone.localdate() + timedelta(days=day))


def seed(owner: User, team: list[User]) -> bool:
    """Run inside the demo tenant. Returns False when the reservations already exist."""
    if Reservation.objects.filter(title=MARKER).exists() or not Item.objects.exists():
        return False
    items = {i.name: i for i in Item.objects.all()}
    packs = {p.name: p for p in Pack.objects.all()}
    methods = ["orange_money", "mtn_momo", "transfer", "cash", "mtn_momo"]
    for index, demo in enumerate(DEMOS):
        lines: list[services.LineInput] = []
        for kind, name, quantity in demo.lines:
            if kind == "pack":
                lines.append(services.LineInput(kind="pack", pack=packs[name], quantity=quantity))
            else:
                lines.append(services.LineInput(kind=kind, item=items[name], quantity=quantity))
        for label, price in demo.services_:
            lines.append(services.LineInput(kind="free", label=label, unit_price=price))
        start, end = demo.day, demo.day + demo.days - 1
        wedding = _wedding(demo, owner) if demo.wedding else None
        data: dict[str, Any] = {
            "client": _client(demo.client, owner),
            "title": demo.title,
            "kind": demo.kind,
            "venue": demo.venue,
            "owner": team[index % 2],
            "vehicle": VEHICLES[index % len(VEHICLES)],
            "wedding": wedding,
            "delivery_at": _at(start - demo.lead, 9),
            "setup_at": _at(start - 1, 14),
            "event_start": _at(start, 15),
            "event_end": _at(end, 23),
            "pickup_at": _at(end + 1, 10),
            "return_at": _at(end + 1, 15),
            "transport_fee": demo.fees[0],
            "setup_fee": demo.fees[1],
            "deposit_pct": int(demo.deposit * 100),
        }
        reservation = services.create_reservation(data, lines, user=owner)
        if demo.oversold:
            # Accepted before the last stock count: 280 Chiavari chairs for 250 (§11). The real
            # confirmation refuses it; the demo forces it to show the shortage alert.
            Reservation.objects.filter(pk=reservation.pk).update(
                status=Status.AWAITING_DEPOSIT, confirmed_at=_at(-1, 11)
            )
            continue
        if demo.status == Status.QUOTE_SENT:
            services.advance(reservation, Status.QUOTE_SENT, user=owner)
            continue
        services.confirm(reservation, user=owner)
        reservation.refresh_from_db()
        confirmed_on = timezone.localdate() + timedelta(days=min(-2, demo.day - 20))
        Reservation.objects.filter(pk=reservation.pk).update(
            confirmed_at=_at((confirmed_on - timezone.localdate()).days, 11)
        )
        collected = round(reservation.total * demo.paid / 1000) * 1000
        if collected:
            deposit = min(collected, reservation.deposit_required) or collected
            services.record_payment(
                reservation,
                amount=deposit,
                method=methods[index % 5],
                paid_at=confirmed_on,
                user=owner,
                reference=f"DEMO-RES-{index:02d}-A",
            )
            if collected - deposit > 0:
                services.record_payment(
                    reservation,
                    amount=collected - deposit,
                    method=methods[(index + 2) % 5],
                    paid_at=_past(demo.day),
                    user=owner,
                    reference=f"DEMO-RES-{index:02d}-B",
                )
        if demo.status == Status.CANCELLED:
            # Its invoices were issued: the cancellation credits all but the kept deposit (§11
            # « 1 avoir après l’annulation »).
            finance_invoicing.issue(reservation, Invoice.Kind.DEPOSIT, user=owner)
            finance_invoicing.issue(reservation, Invoice.Kind.FINAL, user=owner)
            services.cancel(
                reservation, reason="Événement reporté à l’an prochain", user=owner, request=None
            )
            continue
        if demo.status in (Status.AWAITING_DEPOSIT, Status.CONFIRMED):
            continue
        services.advance(reservation, Status.PREPARING, user=owner)
        if demo.status == Status.PREPARING:
            continue
        services.checkout(reservation, None, user=owner)
        steps = {
            Status.INSTALLED: [Status.INSTALLED],
            Status.IN_PROGRESS: [Status.INSTALLED, Status.IN_PROGRESS],
            Status.PICKED_UP: [Status.INSTALLED, Status.IN_PROGRESS, Status.PICKED_UP],
            Status.CLOSED: [Status.PICKED_UP],
        }[Status(demo.status)]
        for step in steps:
            services.advance(reservation, step, user=owner)
        if demo.status == Status.CLOSED:
            counts = {}
            for line in reservation.lines.select_related("item"):
                if line.item and line.item.name in demo.returned and line.kind == "rental":
                    damaged, missing = demo.returned[line.item.name]
                    counts[str(line.pk)] = services.ReturnInput(
                        returned=line.quantity_out - damaged - missing,
                        damaged=damaged,
                        missing=missing,
                    )
            services.process_return(reservation, counts, user=owner)
            reservation.refresh_from_db()
            balance = reservation.total - services.paid(reservation)
            if balance > 0:  # the damage was paid when the return slip was signed
                services.record_payment(
                    reservation,
                    amount=balance,
                    method="cash",
                    paid_at=_past(demo.day + 1),
                    user=owner,
                    reference=f"DEMO-RES-{index:02d}-C",
                )
    assert ReservationPayment.objects.exists()
    return True
