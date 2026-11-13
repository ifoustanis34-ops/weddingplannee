"""Demo suppliers (« Fournisseurs », feedback 13/11/2026): Douala, Yaoundé and Kribi, every
field of the record filled in (services, contact, WhatsApp, address, NIU, RCCM, payment terms,
Mobile Money, bank). All fictitious. Applied at each `seed_demo`: missing suppliers are created,
an existing record only receives its empty fields (or loses an Ivorian +225 number from an older
seed), and the coming weddings get their suppliers once."""

from __future__ import annotations

from datetime import date
from typing import Any

from django.utils import timezone

from events.models import Wedding
from vendors.models import Vendor, VendorAssignment

SUPPLIERS: list[dict[str, Any]] = [
    {
        "name": "Fleurs d’Ébène",
        "kind": "supplier",
        "category": "flowers",
        "contact_name": "Odile Ngo Biyong",
        "phone": "+237 677 41 22 90",
        "whatsapp": "+237 677 41 22 90",
        "email": "contact@fleurs-ebene.cm",
        "city": "Douala",
        "address": "Rue Joss, Bonanjo",
        "tax_id": "M051512345678A",
        "trade_register": "RC/DLA/2018/B/1452",
        "payment_terms": "50 % à la commande, solde à la livraison",
        "mobile_money": "+237 677 41 22 90",
        "bank_details": "Afriland First Bank — 10005 00001 01234567801 45",
        "services": (
            "Décoration florale des salles et des tables, bouquets de "
            "mariée, arches et centres de table."
        ),
        "notes": "Roses importées sur commande 10 jours avant. Livre et installe.",
    },
    {
        "name": "Saveurs du Plateau",
        "kind": "supplier",
        "category": "caterer",
        "contact_name": "Jean-Paul Ekambi",
        "phone": "+237 699 18 54 02",
        "whatsapp": "+237 699 18 54 02",
        "email": "commandes@saveurs-plateau.cm",
        "city": "Douala",
        "address": "Boulevard de la Liberté, Akwa",
        "tax_id": "M061712345690B",
        "trade_register": "RC/DLA/2017/A/0871",
        "payment_terms": "40 % à la réservation, 60 % 7 jours avant",
        "mobile_money": "+237 699 18 54 02",
        "bank_details": "SCB Cameroun — 10002 00010 98765432101 22",
        "services": (
            "Buffets camerounais et internationaux, cocktails, service à "
            "table, vaisselle fournie."
        ),
        "notes": "Buffet camerounais et international, jusqu’à 600 couverts.",
    },
    {
        "name": "Traiteur Mbongo",
        "kind": "supplier",
        "category": "caterer",
        "contact_name": "Hortense Mbongo",
        "phone": "+237 655 30 71 18",
        "whatsapp": "+237 655 30 71 18",
        "email": "traiteur.mbongo@gmail.com",
        "city": "Yaoundé",
        "address": "Bastos, face ambassade du Nigeria",
        "tax_id": "M071912340001C",
        "trade_register": "RC/YAO/2019/B/2210",
        "payment_terms": "50 % à la réservation, solde le jour J",
        "mobile_money": "+237 655 30 71 18",
        "bank_details": "",
        "services": (
            "Cuisine camerounaise (ndolé, poulet DG, brochettes), " "serveurs et maîtres d’hôtel."
        ),
        "notes": "Ndolé, poulet DG, brochettes. Personnel de service compris.",
    },
    {
        "name": "Studio Lumière Akwa",
        "kind": "partner",
        "category": "photographer",
        "contact_name": "Steve Tchinda",
        "phone": "+237 690 22 13 47",
        "whatsapp": "+237 690 22 13 47",
        "email": "studio@lumiere-akwa.cm",
        "city": "Douala",
        "address": "Rue Njo-Njo, Bonapriso",
        "tax_id": "M081812349876D",
        "trade_register": "RC/DLA/2016/B/3390",
        "payment_terms": "30 % à la signature, solde à la remise des photos",
        "mobile_money": "+237 690 22 13 47",
        "bank_details": "Ecobank Cameroun — 10029 26001 31122233344 07",
        "services": (
            "Reportage photo du mariage, séance couple, prises de vue " "par drone, album imprimé."
        ),
        "notes": "Photo et drone. Album remis sous 3 semaines.",
    },
    {
        "name": "Kribi Films",
        "kind": "supplier",
        "category": "videographer",
        "contact_name": "Brice Eyenga",
        "phone": "+237 652 88 01 63",
        "whatsapp": "+237 652 88 01 63",
        "email": "kribifilms@gmail.com",
        "city": "Kribi",
        "address": "Quartier Afan Mabé",
        "tax_id": "M091912341122E",
        "trade_register": "RC/KRI/2019/A/0112",
        "payment_terms": "50 % à la réservation, 50 % à la livraison du film",
        "mobile_money": "+237 652 88 01 63",
        "bank_details": "",
        "services": "Film du mariage, teaser pour les réseaux sociaux, captation de la cérémonie.",
        "notes": "Film de 15 minutes et teaser pour les réseaux sociaux.",
    },
    {
        "name": "DJ Makossa Events",
        "kind": "partner",
        "category": "dj",
        "contact_name": "Cédric Ndoumbè",
        "phone": "+237 678 54 90 21",
        "whatsapp": "+237 678 54 90 21",
        "email": "booking@makossa-events.cm",
        "city": "Douala",
        "address": "Carrefour Ndokoti, Bassa",
        "tax_id": "M101812345566F",
        "trade_register": "RC/DLA/2018/B/2671",
        "payment_terms": "Acompte 50 %, solde avant la soirée",
        "mobile_money": "+237 678 54 90 21",
        "bank_details": "",
        "services": "Animation DJ, maître de cérémonie bilingue, sonorisation de la soirée.",
        "notes": "Animation bilingue, sono jusqu’à 400 invités.",
    },
    {
        "name": "Salle des Fêtes Le Palmier",
        "kind": "partner",
        "category": "venue",
        "contact_name": "Mme Etoundi",
        "phone": "+237 233 42 18 75",
        "whatsapp": "+237 697 42 18 75",
        "email": "reservation@lepalmier-douala.cm",
        "city": "Douala",
        "address": "Bonamoussadi, carrefour Kotto",
        "tax_id": "M111512347788G",
        "trade_register": "RC/DLA/2015/B/0998",
        "payment_terms": "Caution 200 000 FCFA, location réglée 15 jours avant",
        "mobile_money": "+237 697 42 18 75",
        "bank_details": "BICEC — 10001 06810 05432109876 51",
        "services": (
            "Location de la salle (500 places), parking, groupe " "électrogène, office traiteur."
        ),
        "notes": "500 places assises, parking 80 véhicules, groupe électrogène.",
    },
    {
        "name": "Pâtisserie Doux Délices",
        "kind": "supplier",
        "category": "cake",
        "contact_name": "Sandrine Kamga",
        "phone": "+237 694 77 32 08",
        "whatsapp": "+237 694 77 32 08",
        "email": "douxdelices.cm@gmail.com",
        "city": "Yaoundé",
        "address": "Mvog-Mbi, en face de la pharmacie",
        "tax_id": "M122012343344H",
        "trade_register": "RC/YAO/2020/A/1543",
        "payment_terms": "100 % à la commande",
        "mobile_money": "+237 694 77 32 08",
        "bank_details": "",
        "services": "Pièces montées, wedding cakes, mignardises et gâteaux d’anniversaire.",
        "notes": "Pièces montées sur 3 à 5 étages. Commande 2 semaines avant.",
    },
    {
        "name": "Sono Pro Cameroun",
        "kind": "partner",
        "category": "sound",
        "contact_name": "Ferdinand Tagne",
        "phone": "+237 671 09 44 56",
        "whatsapp": "+237 671 09 44 56",
        "email": "contact@sonopro.cm",
        "city": "Douala",
        "address": "Zone industrielle de Bassa",
        "tax_id": "M131412341010J",
        "trade_register": "RC/DLA/2014/B/0457",
        "payment_terms": "Paiement à 30 jours sur facture",
        "mobile_money": "",
        "bank_details": "UBA Cameroun — 10033 05201 12345678901 03",
        "services": "Location de sonorisation, éclairage scénique et écrans LED, avec technicien.",
        "notes": "Location de sono, lumières et écrans LED. Technicien inclus.",
    },
    {
        "name": "Transports Wouri Express",
        "kind": "supplier",
        "category": "transport",
        "contact_name": "Moussa Hamadou",
        "phone": "+237 696 12 60 39",
        "whatsapp": "+237 696 12 60 39",
        "email": "wouriexpress@yahoo.fr",
        "city": "Douala",
        "address": "Rond-point Deïdo",
        "tax_id": "M141612342020K",
        "trade_register": "RC/DLA/2016/A/1789",
        "payment_terms": "Comptant au départ",
        "mobile_money": "+237 696 12 60 39",
        "bank_details": "",
        "services": "Camions pour le matériel, minibus et cars pour les invités, chauffeurs.",
        "notes": "Camions 10 et 20 tonnes, minibus de 30 places pour les invités.",
    },
    {
        "name": "Location Matériel Bonabéri",
        "kind": "partner",
        "category": "rental",
        "contact_name": "Paul Ndjock",
        "phone": "+237 675 33 81 12",
        "whatsapp": "+237 675 33 81 12",
        "email": "lmb.location@gmail.com",
        "city": "Douala",
        "address": "Bonabéri, ancienne route",
        "tax_id": "M151712343030L",
        "trade_register": "RC/DLA/2017/B/2034",
        "payment_terms": "50 % au retrait, solde au retour du matériel",
        "mobile_money": "+237 675 33 81 12",
        "bank_details": "",
        "services": "Complément de chaises, tables, tentes et nappes quand le stock ne suffit pas.",
        "notes": "Complément de chaises, tables et tentes. Quantités à confirmer par appel.",
    },
    {
        "name": "Sécurité Garde Plus",
        "kind": "supplier",
        "category": "security",
        "contact_name": "Capitaine Ewane",
        "phone": "+237 233 47 55 10",
        "whatsapp": "+237 698 47 55 10",
        "email": "operations@gardeplus.cm",
        "city": "Douala",
        "address": "Rue Tokoto, Bali",
        "tax_id": "M161312344040M",
        "trade_register": "RC/DLA/2013/B/0221",
        "payment_terms": "Facture à 15 jours",
        "mobile_money": "",
        "bank_details": "Société Générale Cameroun — 10003 00100 05101234567 88",
        "services": (
            "Agents de sécurité, contrôle d’accès des invités, " "gardiennage du matériel la nuit."
        ),
        "notes": "Agents en tenue et contrôle d’accès des invités.",
    },
    {
        "name": "Emballages & Consommables Akwa",
        "kind": "supplier",
        "category": "supplies",
        "contact_name": "Rachel Mballa",
        "phone": "+237 657 20 93 41",
        "whatsapp": "+237 657 20 93 41",
        "email": "eca.akwa@gmail.com",
        "city": "Douala",
        "address": "Marché Mboppi, porte 3",
        "tax_id": "M172112345050N",
        "trade_register": "RC/DLA/2021/A/3310",
        "payment_terms": "Comptant",
        "mobile_money": "+237 657 20 93 41",
        "bank_details": "",
        "services": (
            "Nappes jetables, serviettes, gobelets, bougies, sachets et " "petites fournitures."
        ),
        "notes": "Nappes jetables, serviettes, gobelets, bougies et petites fournitures.",
    },
]
# `kind` is set at creation only: the agency may change it afterwards.
FIELDS = [key for key in SUPPLIERS[0] if key not in {"name", "kind"}]

# Coming weddings: who works on them, for how much, what was already paid.
BOOKINGS = [
    ("Salle des Fêtes Le Palmier", "Location de la salle", 1_200_000, 600_000),
    ("Saveurs du Plateau", "Buffet pour les invités", 2_400_000, 960_000),
    ("Studio Lumière Akwa", "Photo et drone", 450_000, 135_000),
    ("DJ Makossa Events", "Animation de la soirée", 300_000, 150_000),
    ("Pâtisserie Doux Délices", "Pièce montée", 180_000, 180_000),
    ("Fleurs d’Ébène", "Fleurs de la salle et bouquet", 380_000, 190_000),
]


def _fill(vendor: Vendor, data: dict[str, Any]) -> bool:
    changed = False
    for field in FIELDS:
        current = getattr(vendor, field)
        stale_phone = field in {"phone", "whatsapp", "mobile_money"} and str(current).startswith(
            "+225"
        )
        if (current in ("", None) or stale_phone) and current != data[field]:
            setattr(vendor, field, data[field])
            changed = True
    if changed:
        vendor.save()
    return changed


def _book(today: date) -> int:
    vendors = {v.name: v for v in Vendor.objects.filter(name__in=[b[0] for b in BOOKINGS])}
    booked = 0
    weddings = Wedding.objects.filter(date__gte=today).order_by("date")[:3]
    for index, wedding in enumerate(weddings):
        if VendorAssignment.objects.filter(wedding=wedding).exists():
            continue
        for name, service, cost, paid in BOOKINGS[index : index + 4]:
            vendor = vendors.get(name)
            if vendor is None:
                continue
            VendorAssignment.objects.create(
                wedding=wedding, vendor=vendor, service=service, cost=cost, paid_amount=paid
            )
            booked += 1
    return booked


def seed() -> int:
    """Create or complete the demo suppliers, then book them on the coming weddings."""
    changed = 0
    for data in SUPPLIERS:
        vendor = Vendor.objects.filter(name=data["name"]).first()
        if vendor is None:
            Vendor.objects.create(**data)
            changed += 1
        elif _fill(vendor, data):
            changed += 1
    return changed + _book(timezone.localdate())
