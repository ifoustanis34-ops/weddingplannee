"""Twelve months of activity for the demo agency (reservations-stock.md §11, « Finances »).

Dates are relative to the day the seed runs. Seasonality peaks in December, April and August;
one event is deliberately loss-making (far-away transport) to illustrate profitability. Used by
``seed_demo``; idempotent (skipped once « Mariam & Idriss » exists).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.utils import timezone

from accounts.models import User
from contracts import services as contract_services
from contracts.models import Contract, PaymentSchedule
from crm import services as crm_services
from crm.models import Client
from events import services as event_services
from events.models import Task, Wedding
from finance.defaults import SUBCONTRACTING, ensure_expense_categories
from finance.models import Expense, ExpenseCategory
from quotes import services as quote_services
from quotes.models import Quote

MARKER = "Mariam & Idriss"
GENERIC_LINE = "Organisation et location de matériel"

# Services of the demo quotes, as shares of the total (« Prestations les plus demandées »).
SERVICE_MIXES = [
    [
        ("Coordination complète", 0.2),
        ("Décoration de salle", 0.3),
        ("Location de mobilier et vaisselle", 0.3),
        ("Sonorisation et éclairage", 0.2),
    ],
    [
        ("Décoration de salle", 0.45),
        ("Location de mobilier et vaisselle", 0.4),
        ("Sonorisation et éclairage", 0.15),
    ],
    [("Location de mobilier et vaisselle", 0.6), ("Transport et installation", 0.4)],
    [
        ("Coordination complète", 0.3),
        ("Décoration de salle", 0.4),
        ("Location de mobilier et vaisselle", 0.3),
    ],
]
SALE_MIX = [("Vente de nappes et chandeliers", 0.85), ("Transport et installation", 0.15)]


@dataclass(frozen=True)
class Event:
    client: str
    company: str
    signed: int  # days from today (negative: past)
    wedding: int
    venue: str
    total: int
    cost_ratio: float
    paid: float  # share of the total collected
    cost_label: str = "Prestataires (traiteur, salle, décoration)"


EVENTS = [
    Event("Christelle & Marc", "", -330, -300, "Hôtel Akwa Palace, Douala", 3_800_000, 0.66, 1.0),
    Event("Aïcha & Serge", "", -250, -215, "Espace Diamant, Yaoundé", 4_200_000, 0.67, 1.0),
    Event(
        "Société Orange Events",
        "Orange Events SARL",
        -150,
        -120,
        "Hôtel La Falaise, Douala",
        1_800_000,
        0.62,
        1.0,
    ),
    Event(
        "Estelle & Hervé", "", -110, -95, "Jardins de Bonamoussadi, Douala", 3_500_000, 0.69, 1.0
    ),
    # Deliberately loss-making: transport to Kribi was not charged enough.
    Event(
        "Paroisse Saint-Joseph",
        "",
        -70,
        -60,
        "Paroisse Saint-Joseph, Kribi",
        650_000,
        1.15,
        1.0,
        "Transport lointain et location sur place (Kribi)",
    ),
    Event(
        "Agence Lumière Douala",
        "Agence Lumière",
        -40,
        -35,
        "Douala",
        480_000,
        0.55,
        1.0,
        "Achat des nappes revendues",
    ),
    Event(MARKER, "", -60, 3, "Salle Bellevue, Bonapriso", 4_100_000, 0.71, 0.7),
    Event("Mme Ngo Bassong", "", -25, 12, "Résidence Bassong, Bonapriso", 900_000, 0.62, 0.3),
    Event("Famille Ekotto", "", -20, 20, "Domaine Ekotto, Yaoundé", 1_200_000, 0.63, 0.0),
    Event("Famille Mbarga", "", -5, 40, "Palais des Congrès", 2_600_000, 0.68, 0.3),
]

# category, label, amount, day of month, every n months (1 = monthly)
MONTHLY = [
    ("Loyer de l’entrepôt", "Loyer de l’entrepôt", 150_000, 5, 1),
    ("Électricité et eau", "Facture CIE / SODECI", 35_000, 10, 1),
    ("Frais bancaires et Mobile Money", "Frais bancaires et Mobile Money", 7_500, 28, 1),
    ("Marketing", "Publicité Facebook et Instagram", 40_000, 15, 2),
    ("Maintenance et réparation", "Réparation du groupe électrogène", 120_000, 18, 5),
]
FUEL = [
    62_000,
    58_000,
    71_000,
    90_000,
    66_000,
    74_000,
    95_000,
    70_000,
    64_000,
    81_000,
    69_000,
    88_000,
]


def service_lines(event: Event, index: int) -> list[tuple[str, int]]:
    """Split the total over a few services; the last line takes the rounding."""
    mix = (
        SALE_MIX
        if event.client == "Agence Lumière Douala"
        else SERVICE_MIXES[index % len(SERVICE_MIXES)]
    )
    lines = [(label, round(event.total * share / 1000) * 1000) for label, share in mix[:-1]]
    lines.append((mix[-1][0], event.total - sum(amount for _, amount in lines)))
    return lines


def _aware(day: date) -> datetime:
    return timezone.make_aware(datetime.combine(day, time(11)))


def _month_day(today: date, months_ago: int, day: int) -> date:
    index = today.year * 12 + today.month - 1 - months_ago
    return date(index // 12, index % 12 + 1, min(day, 28))


def seed(owner: User, team: list[User]) -> bool:
    """Run inside the demo tenant. Returns False when the history already exists."""
    _date_wedding_costs()
    if Client.objects.filter(name=MARKER).exists():
        return False
    ensure_expense_categories()
    today = timezone.localdate()
    categories = {c.name: c for c in ExpenseCategory.objects.all()}
    methods = ["transfer", "orange_money", "mtn_momo", "cash", "orange_money"]

    for index, event in enumerate(EVENTS):
        signed = today + timedelta(days=event.signed)
        wedding_day = today + timedelta(days=event.wedding)
        client = crm_services.create_client(
            {"name": event.client, "company": event.company}, user=owner
        )
        quote = quote_services.create_quote(
            {
                "client": client,
                "wedding_date": wedding_day,
                "venue": event.venue,
                "deposit_pct": Decimal("30"),
            },
            [
                quote_services.LineInput(
                    label=label, unit="flat", unit_price=amount, quantity=Decimal(1)
                )
                for label, amount in service_lines(event, index)
            ],
            user=owner,
        )
        quote_services.accept_quote(quote, user=owner)
        contract = quote_services.convert_to_contract(quote, user=owner)
        Quote.objects.filter(pk=quote.pk).update(
            issue_date=signed - timedelta(days=4),
            valid_until=signed + timedelta(days=26),
            sent_at=_aware(signed - timedelta(days=4)),
            accepted_at=_aware(signed),
        )
        Contract.objects.filter(pk=contract.pk).update(signed_at=_aware(signed))
        # Deposit due on signature; the rest 7 days before the event (Ekotto: deposit overdue).
        deposit_due = signed + timedelta(days=8) if event.client == "Famille Ekotto" else signed
        PaymentSchedule.objects.filter(contract=contract, label="Acompte").update(
            due_date=deposit_due
        )
        wedding = Wedding.objects.get(contract=contract)
        wedding.venue = event.venue
        if event.wedding < 0:
            wedding.status = Wedding.Status.DONE
        wedding.save()

        cost_day = wedding_day  # a wedding cost counts in the month of the event
        Expense.objects.create(
            wedding=wedding,
            category=categories[SUBCONTRACTING],
            label=event.cost_label,
            amount=round(event.total * event.cost_ratio / 1000) * 1000,
            date=cost_day,
            supplier="Prestataires partenaires",
            created_by=owner,
        )

        contract.refresh_from_db()
        to_collect = round(event.total * event.paid / 1000) * 1000
        if to_collect:
            deposit = min(to_collect, round(event.total * 0.3 / 1000) * 1000)
            contract_services.record_payment(
                contract,
                amount=deposit,
                method=methods[index % len(methods)],
                paid_at=min(signed, today),
                user=owner,
                reference=f"DEMO-{index:02d}-A",
            )
            rest = to_collect - deposit
            if rest:
                rest_day = min(wedding_day - timedelta(days=7), today)
                contract_services.record_payment(
                    contract,
                    amount=rest,
                    method=methods[(index + 2) % len(methods)],
                    paid_at=max(rest_day, signed),
                    user=owner,
                    reference=f"DEMO-{index:02d}-B",
                )

        if event.wedding >= 0:
            _prepare(wedding, owner, team, today)

    for months_ago in range(12):
        for name, label, amount, day, every in MONTHLY:
            if months_ago % every:
                continue
            when = _month_day(today, months_ago, day)
            if when > today:
                continue
            Expense.objects.create(
                category=categories[name],
                label=label,
                amount=amount,
                date=when,
                method="transfer",
                created_by=owner,
            )
        when = _month_day(today, months_ago, 22)
        if when <= today:
            Expense.objects.create(
                category=categories["Transport et carburant"],
                label="Carburant des véhicules",
                amount=FUEL[months_ago],
                date=when,
                supplier="Total Énergies",
                method="orange_money",
                created_by=owner,
            )
    Expense.objects.create(
        category=categories["Achat de matériel"],
        label="Lot de 50 chaises Chiavari",
        amount=700_000,
        date=_month_day(today, 7, 12),
        supplier="Mobilier Pro Douala",
        method="transfer",
        created_by=owner,
    )
    return True


def _date_wedding_costs() -> None:
    """Undated wedding costs belong to the month of the wedding (older demo data had none)."""
    for expense in Expense.objects.filter(date__isnull=True, wedding__date__isnull=False):
        expense.date = expense.wedding.date
        expense.save(update_fields=["date", "updated_at"])


def _prepare(wedding: Wedding, owner: User, team: list[User], today: date) -> None:
    """Standard tasks; the past ones done, a few for today, one late (alerts, planning)."""
    tasks = event_services.add_standard_tasks(wedding, user=owner)
    # Past standard dates are moved to J+3 by the standard rule: in the demo, they were done.
    catch_up = today + timedelta(days=3)
    for position, task in enumerate(tasks):
        task.assignee = team[position % len(team)]
        if task.due_date and task.due_date <= catch_up:
            task.status = Task.Status.DONE
            task.done_at = timezone.now()
        task.save()
    if wedding.title == MARKER:
        open_tasks = [t for t in tasks if t.status != Task.Status.DONE]
        for task, due, assignee in zip(
            open_tasks,
            [today, today, today - timedelta(days=2), today + timedelta(days=1)],
            [team[1], team[2], team[1], team[0]],
            strict=False,
        ):
            task.due_date = due
            task.assignee = assignee
            task.save()
