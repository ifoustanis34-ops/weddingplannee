"""Demo staff (reservations-stock.md §11 « Personnel »): the 10 people, their assignments on
every live reservation, check-ins on the past ones (2 late, 1 absent), last month's pay
validated and paid, this month's in progress. Didier Kra (team lead) and Linda Abena (staff)
get a login to show « Mes missions ». Idempotent: does nothing once staff exists."""

from __future__ import annotations

from datetime import date, timedelta

from django.utils import timezone

from accounts.models import Membership, User
from core.exceptions import BusinessError
from core.tenant import require_current_organization
from reservations.models import Reservation
from staff import services
from staff.models import Assignment, StaffMember, StaffTask

from .seed_demo import DEMO_PASSWORD as PASSWORD

PEOPLE = [
    # name, position, kind, pay mode, rate, phone, login email (role)
    ("Awa Sangaré", "Wedding planner", "employee", "monthly", 250_000, "+237 621 12 23 34", None),
    ("Didier Kra", "Chef d’équipe", "employee", "monthly", 200_000, "+237 606 67 78 89",
     ("didier.kra@maison-elegance.ci", Membership.Role.TEAM_LEAD)),
    ("Nadège Brou", "Comptable", "employee", "monthly", 220_000, "+237 664 45 56 67", None),
    ("Joël Mbarga", "Magasinier", "employee", "monthly", 150_000, "+237 629 08 07 06", None),
    ("Serge Atangana", "Chauffeur livreur", "employee", "monthly", 140_000, "+237 601 21 31 41",
     None),
    ("Brice Ndzana", "Installateur", "day_worker", "daily", 8_000, "+237 622 12 22 32", None),
    ("Mireille Fotso", "Décoratrice", "freelance", "mission", 40_000, "+237 663 13 23 33", None),
    ("Carine Essomba", "Hôtesse", "day_worker", "daily", 10_000, "+237 604 14 24 34", None),
    ("Patrick Nkolo", "Installateur", "day_worker", "daily", 8_000, "+237 625 15 25 35", None),
    ("Linda Abena", "Serveuse", "day_worker", "daily", 7_000, "+237 666 16 26 36",
     ("linda.abena@maison-elegance.ci", Membership.Role.STAFF)),
]  # fmt: skip
LIVE = (
    "awaiting_deposit",
    "confirmed",
    "preparing",
    "delivered",
    "installed",
    "in_progress",
    "picked_up",
    "closed",
)


def _login(name: str, phone: str, email: str, role: str) -> User:
    user, created = User.objects.get_or_create(
        email=email, defaults={"full_name": name, "phone": phone, "is_verified": True}
    )
    if created:
        user.set_password(PASSWORD)
        user.save(update_fields=["password"])
    Membership.objects.update_or_create(
        user=user,
        organization=require_current_organization(),
        defaults={"role": role, "is_active": True, "joined_at": timezone.now()},
    )
    return user


def _assign(
    reservation: Reservation, person: StaffMember, step: str, role: str, owner: User
) -> Assignment | None:
    try:
        assignment, _ = services.assign(reservation, person, step=step, role=role, user=owner)
    except BusinessError:
        return None  # a step without a time on this reservation
    return assignment


DEPARTMENTS = {
    "Wedding planner": "Événementiel",
    "Chef d’équipe": "Logistique",
    "Comptable": "Finances",
    "Magasinier": "Logistique",
    "Chauffeur livreur": "Logistique",
    "Installateur": "Logistique",
    "Décoratrice": "Décoration",
    "Hôtesse": "Accueil",
    "Serveuse": "Service",
}


def fill_departments() -> None:
    """The badge's « Département » line (feedback 13/11/2026), also for an already seeded base."""
    for position, department in DEPARTMENTS.items():
        StaffMember.objects.filter(position=position, department="").update(department=department)


def seed(owner: User) -> bool:
    if StaffMember.objects.exists():
        fill_departments()
        return False
    people: dict[str, StaffMember] = {}
    for name, position, kind, mode, rate, phone, login in PEOPLE:
        user = _login(name, phone, *login) if login else None
        people[name] = StaffMember.objects.create(
            full_name=name,
            position=position,
            kind=kind,
            pay_mode=mode,
            pay_rate=rate,
            phone=phone,
            mobile_money=phone,
            user=user,
            emergency_contact="Famille — " + phone,
            skills={
                "Décoratrice": ["Drapé", "Art floral"],
                "Installateur": ["Montage de tentes"],
            }.get(position, []),
            created_by=owner,
        )

    fill_departments()
    now = timezone.now()
    past: list[Assignment] = []
    for index, reservation in enumerate(
        Reservation.objects.filter(status__in=LIVE).order_by("event_start")
    ):
        crew = [
            (people["Didier Kra"], "all", "Chef d’équipe"),
            (people["Serge Atangana"], "delivery", "Chauffeur"),
            (people["Serge Atangana"], "pickup", "Chauffeur"),
            (people["Brice Ndzana" if index % 2 else "Patrick Nkolo"], "setup", "Installation"),
            (people["Carine Essomba"], "event", "Accueil des invités"),
            (people["Linda Abena"], "event", "Service"),
        ]
        if reservation.kind in ("service", "mixed"):
            crew.append((people["Mireille Fotso"], "setup", "Décoration"))
        for person, step, role in crew:
            assignment = _assign(reservation, person, step, role, owner)
            if assignment is not None and assignment.end < now:
                past.append(assignment)

    # Tasks per person and per event (§7), done for what is behind us.
    tasks = {
        "Didier Kra": [
            "Vérifier le bon de sortie avec le magasinier",
            "Briefing de l’équipe sur place",
        ],
        "Serge Atangana": ["Charger le camion la veille", "Faire signer le bon de livraison"],
        "Brice Ndzana": ["Monter les tables et les chaises", "Photo de fin d’installation"],
        "Patrick Nkolo": ["Monter les tables et les chaises", "Photo de fin d’installation"],
        "Mireille Fotso": ["Composer l’arche florale", "Habiller la table d’honneur"],
        "Carine Essomba": ["Accueillir et placer les invités"],
        "Linda Abena": ["Dresser les tables (verres, assiettes, couverts)"],
    }
    for assignment in Assignment.objects.select_related("staff", "reservation"):
        for title in tasks.get(assignment.staff.full_name, []):
            if StaffTask.objects.filter(
                staff=assignment.staff, reservation=assignment.reservation, title=title
            ).exists():
                continue
            StaffTask.objects.create(
                staff=assignment.staff,
                reservation=assignment.reservation,
                title=title,
                # Older missions validated, the last two days still waiting for validation.
                status=(
                    StaffTask.Status.TODO
                    if assignment.end >= now
                    else (
                        StaffTask.Status.VALIDATED
                        if assignment.end < now - timedelta(days=2)
                        else StaffTask.Status.DONE
                    )
                ),
                comment="RAS" if assignment.end < now else "",
                done_at=assignment.end if assignment.end < now else None,
                done_by=assignment.staff.user or owner if assignment.end < now else None,
                validated_at=(
                    assignment.end + timedelta(hours=12)
                    if assignment.end < now - timedelta(days=2)
                    else None
                ),
                validated_by=owner if assignment.end < now - timedelta(days=2) else None,
                created_by=owner,
            )

    # Check-ins of the missions already done: 2 late arrivals, 1 absence (§11).
    for number, assignment in enumerate(past):
        if number == 3:
            services.mark_absent(assignment, user=owner, note="Malade, prévenu la veille")
            continue
        delay = timedelta(minutes=35 if number in (1, 6) else 0)
        services.check_in(assignment, user=owner, at=assignment.start + delay)
        # A working day, even on a several-day « toute la réservation » assignment.
        out = min(assignment.end, assignment.start + delay + timedelta(hours=10))
        services.check_out(assignment, user=owner, at=out)

    # Last month's pay: validated and paid; this month's: in progress.
    today = timezone.localdate()
    first = today.replace(day=1)
    last_month_end = first - timedelta(days=1)
    previous = services.create_period(last_month_end.replace(day=1), last_month_end, user=owner)
    services.validate(previous, user=owner)
    for line in previous.lines.filter(total__gt=0):
        method = "transfer" if line.staff.kind == "employee" else "orange_money"
        services.pay_line(line, method=method, paid_at=date(first.year, first.month, 2), user=owner)
    next_month = (first + timedelta(days=32)).replace(day=1)
    services.create_period(first, next_month - timedelta(days=1), user=owner)
    return True
