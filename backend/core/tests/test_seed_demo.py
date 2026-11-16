import pytest
from django.core.management import call_command

from accounts.models import Membership
from organizations.models import Organization


@pytest.mark.django_db
def test_seed_demo_is_idempotent() -> None:
    call_command("seed_demo")
    call_command("seed_demo")

    organization = Organization.objects.get(slug="maison-elegance")
    assert organization.name == "Maison Élégance Events"
    assert (organization.city, organization.country) == ("Douala", "CM")
    assert (organization.currency, organization.timezone) == ("XAF", "Africa/Douala")
    roles = set(Membership.objects.filter(organization=organization).values_list("role", flat=True))
    # The team lead and a staff member log in to « Mes missions » (§7); the storekeeper too, so
    # the presentation mode shows every point of view (16/11/2026).
    assert roles == {
        "owner",
        "planner",
        "assistant",
        "accountant",
        "storekeeper",
        "team_lead",
        "staff",
    }

    from core.tenant import tenant_context
    from staff.models import Attendance, PayPeriod, StaffMember

    with tenant_context(organization):
        assert StaffMember.objects.count() == 10
        statuses = list(Attendance.objects.values_list("status", flat=True))
        assert statuses.count("absent") == 1 and statuses.count("late") == 2
        assert sorted(PayPeriod.objects.values_list("status", flat=True)) == ["draft", "paid"]


@pytest.mark.django_db
def test_seed_demo_gives_two_agencies_their_own_identity() -> None:
    from core.tenant import tenant_context
    from documents.models import OrganizationBranding

    call_command("seed_demo")
    call_command("seed_demo")

    identities = {}
    for slug in ("maison-elegance", "atelier-bassam"):
        with tenant_context(Organization.objects.get(slug=slug)):
            identities[slug] = OrganizationBranding.objects.get()
    maison, atelier = identities["maison-elegance"], identities["atelier-bassam"]
    assert maison.primary_color == "#0F1B3D" and atelier.primary_color == "#0B4D3B"
    assert maison.logo.name.endswith(".svg") and atelier.logo.name.endswith(".svg")
    assert maison.logo.name != atelier.logo.name
    assert maison.tax_ids["rccm"] == "RC/DLA/2019/B/1234"


@pytest.mark.django_db
def test_seed_demo_matches_the_fictional_data_of_section_11() -> None:
    """docs/specs/reservations-stock.md §11, checked on the seeded agency."""
    from collections import Counter

    from alerts import services as alert_services
    from alerts.models import Alert
    from core.tenant import tenant_context
    from crm.models import Client
    from finance import invoicing, profitability
    from finance.models import CreditNote, Invoice
    from finance.periods import resolve
    from reservations.models import Reservation
    from stock.models import Item, Pack, PartnerSupply

    call_command("seed_demo")
    with tenant_context(Organization.objects.get(slug="maison-elegance")):
        assert Item.objects.filter(total_quantity__gt=0).count() == 30  # ours (§11)
        assert Pack.objects.count() == 4
        # Partner equipment (14/11/2026): 7 offers, one item only a partner has.
        assert PartnerSupply.objects.count() == 7
        assert Item.objects.filter(total_quantity=0, partner_supplies__isnull=False).count() == 1
        reservations = list(Reservation.objects.all())
        assert len(reservations) == 12
        assert Counter(r.status for r in reservations) == {
            "closed": 2,
            "picked_up": 1,
            "in_progress": 1,
            "installed": 1,
            "preparing": 2,
            "confirmed": 3,
            "awaiting_deposit": 1,
            "cancelled": 1,
        }
        weddings = [r for r in reservations if r.wedding_id]
        assert len(weddings) == 5
        assert Counter(r.kind for r in reservations if not r.wedding_id) == {
            "rental": 4,
            "sale": 2,
            "mixed": 1,
        }
        assert min(r.total for r in reservations) >= 150_000
        assert max(r.total for r in reservations) <= 4_200_000
        assert Client.objects.filter(is_deleted=False, is_archived=False).count() == 15

        invoices = list(Invoice.objects.all())
        states = invoicing.states(invoices)
        assert sum(s.status == "overdue" for s in states.values()) == 2
        note = CreditNote.objects.get()
        assert note.reservation.status == "cancelled"

        alert_services.refresh()
        kinds = Counter(
            Alert.objects.filter(resolved_at__isnull=True).values_list("kind", flat=True)
        )
        assert kinds["stock_shortage"] >= 1 and kinds["late_return"] >= 1
        assert kinds["overdue_invoice"] == 2
        assert Alert.objects.filter(
            kind="below_threshold", title__icontains="Verre à pied"
        ).exists()

        from django.utils import timezone

        year = resolve("year", timezone.localdate())
        events = profitability.by_event(year)
        assert any(row["margin"] < 0 and row["kind"] == "reservation" for row in events)
