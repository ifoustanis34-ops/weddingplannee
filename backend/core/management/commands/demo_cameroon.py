# ruff: noqa: E501  (a table of demo contacts, read line by line)
"""Cameroonian details of the demo agency (feedback 13/11/2026): fictional +237 numbers,
addresses in Douala and Yaoundé, Cameroonian venues. Applied at every `seed_demo`: it also
converts a database seeded before the move from Abidjan, without deleting anything."""

from __future__ import annotations

import re

from accounts.models import User
from crm.models import Client, phone_key
from events.models import Wedding
from reservations.models import Reservation
from staff.models import StaffMember

# name: (company, phone, email, address) — fictional numbers (MTN 67x/68x/650-654, Orange
# 69x/655-659, landlines 233 Douala and 222 Yaoundé).
CLIENTS = {
    "Agence Lumière Douala": ("Agence Lumière SARL", "+237 699 41 22 18", "contact@agence-lumiere-demo.cm", "Rue Joss, Bonanjo, Douala"),
    "Aïcha & Serge": ("", "+237 677 25 41 90", "aicha.serge@gmail.com", "Bastos, Yaoundé"),
    "Christelle & Marc": ("", "+237 694 11 73 05", "christelle.marc@yahoo.fr", "Bonamoussadi, Douala"),
    "Estelle & Hervé": ("", "+237 655 82 30 47", "estelle.herve@gmail.com", "Akwa, Douala"),
    "Famille Diabaté": ("", "+237 670 14 56 92", "famille.diabate@gmail.com", "Makepe, Douala"),
    "Famille Ekotto": ("", "+237 699 58 21 76", "ekotto.famille@gmail.com", "Odza, Yaoundé"),
    "Famille Kouamé": ("", "+237 678 33 90 12", "kouame.famille@yahoo.fr", "Logpom, Douala"),
    "Famille Mbarga": ("", "+237 696 47 15 83", "mbarga.famille@gmail.com", "Mvog-Mbi, Yaoundé"),
    "Famille Tchouta": ("", "+237 681 22 64 09", "famille.tchouta@outlook.com", "Bonamoussadi, Douala"),
    "Grâce & Yannick": ("", "+237 677 64 28 31", "grace.yannick@gmail.com", "Bastos, Yaoundé"),
    "Mariam & Idriss": ("", "+237 675 90 18 44", "mariam.idriss@gmail.com", "Bonapriso, Douala"),
    "Mme Ngo Bassong": ("", "+237 699 03 77 25", "ngo.bassong@yahoo.fr", "Bonapriso, Douala"),
    "Nadia & Koffi": ("", "+237 690 55 43 21", "nadia.koffi@gmail.com", "Bonapriso, Douala"),
    "Paroisse Saint-Joseph": ("Paroisse catholique Saint-Joseph", "+237 233 42 18 60", "secretariat.stjoseph@gmail.com", "Akwa, Douala"),
    "Société Orange Events": ("Orange Events SARL", "+237 222 23 45 67", "contact@orange-events-demo.cm", "Hippodrome, Yaoundé"),
}  # fmt: skip

# Venues of a database seeded in Abidjan → their Cameroonian counterparts.
VENUES = {
    "Paroisse Saint-Joseph, Treichville": "Paroisse Saint-Joseph, Akwa, Douala",
    "Sofitel Abidjan Hôtel Ivoire": "Hôtel Sawa, Douala",
    "Jardins de Bingerville": "Jardins de Bonamoussadi, Douala",
    "Salle Bellevue, Cocody": "Salle Bellevue, Bonapriso",
    "Espace Latrille, Abidjan": "Espace Diamant, Bastos, Yaoundé",
    "Hôtel Ivoire, Abidjan": "Hilton, Yaoundé",
    "Hôtel Ivoire": "Hôtel Akwa Palace, Douala",
    "Espace Latrille": "Espace Diamant, Yaoundé",
    "Sofitel Abidjan": "Hôtel La Falaise, Douala",
    "Résidence Kouamé, Cocody": "Résidence Kouamé, Logpom, Douala",
}
IVORIAN = re.compile(r"\+225 ?0?(\d) ?(\d\d) ?(\d\d) ?(\d\d) ?(\d\d)")


def to_cameroon(phone: str) -> str:
    """« +225 07 08 12 34 56 » → a fictional Cameroonian mobile « +237 6XX XX XX XX »."""

    def convert(match: re.Match[str]) -> str:
        first, a, b, c, d = match.groups()
        digits = f"6{(int(first) + 5) % 10}{a}{b}{c}{d}"[:9]
        return f"+237 {digits[0:3]} {digits[3:5]} {digits[5:7]} {digits[7:9]}"

    return IVORIAN.sub(convert, phone)


def apply() -> int:
    """Run inside the demo tenant. Returns how many records changed."""
    changed = 0
    for client in Client.objects.all():
        before = (client.company, client.phone, client.email, client.address)
        if client.name in CLIENTS:
            company, phone, email, address = CLIENTS[client.name]
            client.company = client.company or company
            client.phone, client.address = phone, address
            client.email = client.email or email
        else:
            client.phone = to_cameroon(client.phone)
            client.phone_alt = to_cameroon(client.phone_alt)
        client.phone_key = phone_key(client.phone)
        if before != (client.company, client.phone, client.email, client.address):
            client.save()
            changed += 1
    for model in (Reservation, Wedding):
        for old, new in VENUES.items():
            changed += model.objects.filter(venue=old).update(venue=new)
    for staff in StaffMember.objects.all():
        fields = ("phone", "mobile_money", "emergency_contact")
        before = tuple(getattr(staff, f) for f in fields)
        for field in fields:
            setattr(staff, field, to_cameroon(getattr(staff, field)))
        if before != tuple(getattr(staff, f) for f in fields):
            staff.save(update_fields=[*fields, "updated_at"])
            changed += 1
    for user in User.objects.filter(phone__startswith="+225"):
        user.phone = to_cameroon(user.phone)
        user.save(update_fields=["phone"])
        changed += 1
    return changed
