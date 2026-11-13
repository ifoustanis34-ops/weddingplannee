"""Demo data: the « Maison Élégance Events » agency in Douala (Cameroon), and a second agency
with another identity (« Atelier Kribi Mariages ») to check the documents. Safe to run several
times."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Membership, User
from catalog.defaults import create_sample_catalog
from catalog.models import ServiceCategory, ServiceItem
from contracts import services as contract_services
from contracts.models import Contract
from core.tenant import tenant_context
from crm import services as crm_services
from crm.models import Client
from documents import demo as branding_demo
from finance.models import Expense
from organizations import services as organization_services
from organizations.models import Organization
from quotes import services as quote_services

DEMO_SLUG = "maison-elegance"
DEMO_PASSWORD = "Wedivo-demo-2026"
SECOND_SLUG = "atelier-bassam"
SECOND_OWNER = ("koffi.nguessan@atelier-bassam.ci", "Koffi N’Guessan", "+237 625 93 32 21")
DEMO_TEAM = [
    ("aicha.kone@maison-elegance.ci", "Aïcha Koné", "+237 620 81 23 45", Membership.Role.OWNER),
    (
        "yao.kouassi@maison-elegance.ci",
        "Yao Kouassi",
        "+237 604 42 10 98",
        Membership.Role.PLANNER,
    ),
    (
        "mariam.traore@maison-elegance.ci",
        "Mariam Traoré",
        "+237 662 34 56 78",
        Membership.Role.ASSISTANT,
    ),
    (
        "serge.bamba@maison-elegance.ci",
        "Serge Bamba",
        "+237 627 76 54 32",
        Membership.Role.ACCOUNTANT,
    ),
]


# Guests of the demo wedding: name, seats, category, table.
DEMO_GUESTS = [
    ("Famille Kouassi", 4, "Famille", "3"),
    ("Famille Traoré", 5, "Famille", "4"),
    ("M. et Mme Bamba", 2, "VIP", "1"),
    ("Aya Koffi", 1, "Standard", "7"),
    ("Famille N’Guessan", 6, "Famille", "5"),
    ("Dr Ouattara", 2, "VIP", "1"),
    ("Collègues de Nadia", 8, "Standard", "9"),
    ("Mme Diabaté", 1, "Standard", "7"),
]


# Demo clients (docs/specs/reservations-stock.md §11; the full list of 15 comes with step S9).
# name, company, phone, email, address, notes
DEMO_CLIENTS = [
    (
        "Nadia & Koffi",
        "",
        "+237 621 12 23 34",
        "nadia.koffi@gmail.com",
        "Bonapriso, Douala",
        "Mariage de 500 invités, décoration émeraude et or.",
    ),
]


class Command(BaseCommand):
    help = "Create (or refresh) the Maison Élégance Events demo organization."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        organization = Organization.objects.filter(slug=DEMO_SLUG).first()
        if organization is None:
            organization = organization_services.create_organization(
                name="Maison Élégance Events",
                slug=DEMO_SLUG,
                city="Douala",
                country="CM",
                weddings_per_year=40,
            )
        organization.weddings_enabled = True  # the demo shows the « Mariages » module too
        organization.legal_mentions = (
            "Maison Élégance Events SARL · RC/DLA/2019/B/1234 · NIU M061912345678A · "
            "Rue Njo-Njo, Bonapriso, Douala"
        )
        # A Cameroonian agency (feedback 13/11/2026): Douala, FCFA of Central Africa, local time.
        organization.city, organization.country = "Douala", "CM"
        organization.currency, organization.timezone = "XAF", "Africa/Douala"
        organization.save(
            update_fields=[
                "legal_mentions",
                "weddings_enabled",
                "city",
                "country",
                "currency",
                "timezone",
                "updated_at",
            ]
        )
        organization_services.invalidate_organization(organization)

        for email, full_name, phone, role in DEMO_TEAM:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={"full_name": full_name, "phone": phone, "is_verified": True},
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save(update_fields=["password"])
            Membership.objects.update_or_create(
                user=user,
                organization=organization,
                defaults={"role": role, "is_active": True, "joined_at": timezone.now()},
            )

        with tenant_context(organization):
            if not ServiceCategory.objects.exists():
                create_sample_catalog()
                self.stdout.write("Catalogue d’exemple créé.")
            branding_demo.apply(branding_demo.MAISON_ELEGANCE, branding_demo.MAISON_LOGO)
        self._seed_clients(organization)
        self._seed_second_agency()

        self.stdout.write(self.style.SUCCESS(f"Espace « {organization.name} » prêt ({DEMO_SLUG})."))
        self.stdout.write(f"Mot de passe des comptes de démonstration : {DEMO_PASSWORD}")
        for email, _, _, role in DEMO_TEAM:
            self.stdout.write(f"  {role:<10} {email}")
        self.stdout.write(f"  {'owner':<10} {SECOND_OWNER[0]} (Atelier Kribi Mariages)")

    def _seed_second_agency(self) -> None:
        """Another agency, another identity: its documents must never look like the first one's."""
        organization = Organization.objects.filter(slug=SECOND_SLUG).first()
        if organization is None:
            organization = organization_services.create_organization(
                name="Atelier Kribi Mariages",
                slug=SECOND_SLUG,
                city="Kribi",
                country="CM",
                weddings_per_year=10,
            )
        organization.currency, organization.timezone = "XAF", "Africa/Douala"
        organization.save(update_fields=["currency", "timezone", "updated_at"])
        email, full_name, phone = SECOND_OWNER
        user, created = User.objects.get_or_create(
            email=email, defaults={"full_name": full_name, "phone": phone, "is_verified": True}
        )
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save(update_fields=["password"])
        Membership.objects.update_or_create(
            user=user,
            organization=organization,
            defaults={
                "role": Membership.Role.OWNER,
                "is_active": True,
                "joined_at": timezone.now(),
            },
        )
        with tenant_context(organization):
            if not ServiceCategory.objects.exists():
                create_sample_catalog()
            branding_demo.apply(branding_demo.ATELIER_BASSAM, branding_demo.ATELIER_LOGO)

    def _seed_clients(self, organization: Organization) -> None:
        """Demo clients, created once (matched by name)."""
        owner = User.objects.get(email=DEMO_TEAM[0][0])
        created = 0
        with tenant_context(organization):
            existing = set(Client.objects.values_list("name", flat=True))
            for name, company, phone, email, address, notes in DEMO_CLIENTS:
                if name in existing:
                    continue
                created += 1
                crm_services.create_client(
                    {
                        "name": name,
                        "company": company,
                        "phone": phone,
                        "email": email,
                        "address": address,
                        "notes": notes,
                    },
                    user=owner,
                )
        self.stdout.write(f"{created} clients de démonstration créés.")
        self._seed_contract(organization)
        self._seed_guests(organization)
        self._seed_history(organization)
        self._seed_stock(organization)
        self._seed_reservations(organization)

    def _seed_history(self, organization: Organization) -> None:
        """Twelve months of contracts, payments and expenses (dashboard, finances)."""
        from .demo_history import seed

        team = [User.objects.get(email=email) for email, *_ in DEMO_TEAM]
        with tenant_context(organization), transaction.atomic():
            if seed(team[0], team):
                self.stdout.write("Historique de 12 mois (contrats, paiements, dépenses) créé.")

    def _seed_stock(self, organization: Organization) -> None:
        """30 articles, 4 packs, maintenance and out-of-service equipment (stock screens)."""
        from .demo_stock import seed

        owner = User.objects.get(email=DEMO_TEAM[0][0])
        with tenant_context(organization), transaction.atomic():
            if seed(owner):
                self.stdout.write("Stock de démonstration créé (30 articles, 4 packs).")

    def _seed_reservations(self, organization: Organization) -> None:
        """13 reservations over six weeks around today (reservations screens, dashboard)."""
        from .demo_reservations import seed

        team = [User.objects.get(email=email) for email, *_ in DEMO_TEAM]
        with tenant_context(organization), transaction.atomic():
            if seed(team[0], team[:2]):
                self.stdout.write("Réservations de démonstration créées.")
        from .demo_invoices import seed as seed_invoices

        with tenant_context(organization), transaction.atomic():
            if seed_invoices(team[0]):
                self.stdout.write("Factures et avoir de démonstration créés.")
        from .demo_staff import seed as seed_staff

        with tenant_context(organization), transaction.atomic():
            if seed_staff(team[0]):
                self.stdout.write("Personnel, affectations, présences et paie créés.")
        from .demo_vendors import seed as seed_vendors

        with tenant_context(organization), transaction.atomic():
            if seed_vendors():
                self.stdout.write("Fournisseurs de démonstration complétés.")
        from .demo_cameroon import apply as cameroon

        with tenant_context(organization), transaction.atomic():
            changed = cameroon()
            if changed:
                self.stdout.write(f"Coordonnées camerounaises appliquées ({changed} fiches).")

    def _seed_guests(self, organization: Organization) -> None:
        """Guests and tickets of « Nadia & Koffi » (screen Billets, devis-billets.md §6)."""
        from events.models import Wedding
        from invitations import services as ticket_services
        from invitations.models import Guest

        owner = User.objects.get(email=DEMO_TEAM[0][0])
        with tenant_context(organization):
            wedding = Wedding.objects.filter(title__icontains="Nadia").first()
            if wedding is None or Guest.objects.filter(wedding=wedding).exists():
                return
            design = ticket_services.get_design(wedding)
            ticket_services.update_design(
                design,
                {
                    "palette": "emeraude-or",
                    "venue": design.venue or "Salle Bellevue",
                    "address": "Bonanjo, Douala",
                    "dress_code": "Pagne et or",
                    "show_monogram": True,
                },
            )
            for name, seats, category, table in DEMO_GUESTS:
                ticket_services.create_guest(
                    wedding,
                    {"name": name, "seats": seats, "category": category, "table": table},
                    user=owner,
                )
            for guest in Guest.objects.filter(wedding=wedding).order_by("name")[:5]:
                ticket_services.generate(ticket_services.issue_ticket(guest, user=owner))
        self.stdout.write("Invités et billets de démonstration créés.")

    def _seed_contract(self, organization: Organization) -> None:
        """A signed contract with expenses and payments spread over months (dashboard, finances)."""
        owner = User.objects.get(email=DEMO_TEAM[0][0])
        with tenant_context(organization):
            client = Client.objects.filter(name="Nadia & Koffi").first()
            if client is None or Contract.objects.filter(client=client).exists():
                return
            items = {item.name: item for item in ServiceItem.objects.all()}
            lines = [
                quote_services.LineInput(
                    label=name,
                    unit=items[name].unit,
                    unit_price=items[name].unit_price,
                    quantity=Decimal(quantity),
                    service_item=items[name],
                )
                for name, quantity in [
                    ("Accompagnement complet (6 mois)", "1"),
                    ("Menu traiteur ivoirien", "500"),
                    ("Décoration de salle", "1"),
                    ("Orchestre", "1"),
                ]
            ]
            quote = quote_services.create_quote(
                {
                    "client": client,
                    "deposit_pct": Decimal("30"),
                    "wedding_date": timezone.localdate() + timedelta(days=45),
                    "guest_count": 500,
                },
                lines,
                user=owner,
            )
            quote_services.accept_quote(quote, user=owner)
            contract = quote_services.convert_to_contract(quote, user=owner)
            for label, amount in [
                ("Traiteur (500 couverts)", 4_200_000),
                ("Orchestre", 550_000),
                ("Fleurs et décoration", 700_000),
            ]:
                Expense.objects.create(
                    wedding=contract.wedding,
                    label=label,
                    amount=amount,
                    date=contract.wedding_date,
                    created_by=owner,
                )
            today = timezone.localdate()
            for days_ago, amount, method in [
                (75, 1_500_000, "transfer"),
                (40, 1_200_000, "orange_money"),
                (8, 800_000, "mtn_momo"),
            ]:
                contract_services.record_payment(
                    contract,
                    amount=amount,
                    method=method,
                    user=owner,
                    paid_at=today - timedelta(days=days_ago),
                    reference=f"DEMO-{days_ago}",
                )
            self.stdout.write(f"Contrat {contract.number} et paiements de démonstration créés.")
