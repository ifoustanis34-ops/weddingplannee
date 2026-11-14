"""Import of the equipment lists (feedback 14/11/2026): ours and the partners', one sheet.

Columns (titles in any order, accents and case ignored):

    Type             « Interne » (our equipment) or « Partenaire »; empty: Partenaire when the
                     Partenaire column is filled, else Interne
    Article          name (required)
    Catégorie        created when unknown (default « Divers »)
    Référence        optional, matches an existing item first
    Quantité         ours: the exact stock we own; partner: what the partner can lend
    Prix location    rent price to the client (FCFA)
    Caution          per unit
    Coût achat       replacement price of our equipment
    Partenaire       partner name (created in the « Fournisseurs » directory when unknown)
    Téléphone        partner phone (new partners)
    Prix partenaire  what the partner charges us per unit and per event

Our quantities are set exactly: the difference becomes an inventory adjustment (traced).
"""

from __future__ import annotations

import io
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from accounts.models import User
from core.exceptions import BusinessError
from core.spreadsheets import read_table
from vendors.models import Vendor

from .models import Item, ItemCategory, PartnerSupply, StockMovement
from .services import create_item, record_movement

COLUMNS: dict[str, tuple[str, ...]] = {
    "type": ("type", "origine", "source"),
    "name": ("article", "nom", "designation", "materiel", "libelle"),
    "category": ("categorie", "famille"),
    "reference": ("reference", "ref", "code"),
    "quantity": ("quantite", "qte", "nombre", "stock"),
    "rent_price": ("prix location", "prix de location", "tarif location", "prix"),
    "deposit": ("caution",),
    "purchase_cost": ("cout achat", "cout d achat", "prix achat", "prix d achat", "valeur"),
    "partner": ("partenaire", "fournisseur", "nom du partenaire"),
    "partner_phone": ("telephone", "telephone partenaire", "tel", "contact"),
    "unit_cost": ("prix partenaire", "cout partenaire", "tarif partenaire", "cout location"),
}
TEMPLATE_HEADERS = [
    "Type",
    "Article",
    "Catégorie",
    "Référence",
    "Quantité",
    "Prix location",
    "Caution",
    "Coût achat",
    "Partenaire",
    "Téléphone",
    "Prix partenaire",
]
PHONE = "+237 6 99 00 00 00"
TEMPLATE_ROWS = [
    ["Interne", "Chaise Chiavari dorée", "Mobilier", "", 200, 1500, 500, 25000, "", "", ""],
    ["Partenaire", "Chaise Chiavari dorée", "Mobilier", "", 300, "", "", "", "Déco Prestige",
     PHONE, 700],
    ["Partenaire", "Arche florale", "Décoration", "", 2, 75000, 20000, "", "Fleurs du Wouri",
     "", 40000],
]  # fmt: skip


def _norm(text: Any) -> str:
    raw = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return " ".join(raw.lower().replace("’", " ").replace("'", " ").replace("_", " ").split())


def _columns(headers: list[str]) -> dict[str, int]:
    found: dict[str, int] = {}
    normalized = [_norm(h) for h in headers]
    for key, names in COLUMNS.items():
        for index, header in enumerate(normalized):
            if header in names and index not in found.values():
                found[key] = index
                break
    if "name" not in found:
        raise BusinessError(
            "import_columns",
            "Colonne « Article » introuvable : téléchargez le modèle pour voir les titres "
            "attendus.",
        )
    return found


def _amount(value: Any, label: str, row: int) -> int | None:
    if value in (None, ""):
        return None
    text = str(value).replace(" ", "").replace("\xa0", "").replace(" ", "")
    text = text.replace("FCFA", "").replace("F", "").replace(",", ".")
    try:
        number = float(text)
    except ValueError as exc:
        raise ValueError(f"ligne {row} : « {label} » n’est pas un nombre ({value}).") from exc
    if number < 0:
        raise ValueError(f"ligne {row} : « {label} » ne peut pas être négatif.")
    return round(number)


@dataclass
class Report:
    items_created: int = 0
    items_updated: int = 0
    stock_adjusted: int = 0
    partners_created: int = 0
    supplies_created: int = 0
    supplies_updated: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    dry_run: bool = False

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


class _Rows:
    def __init__(self, user: User, report: Report) -> None:
        self.user = user
        self.report = report
        self.categories: dict[str, ItemCategory] = {
            _norm(c.name): c for c in ItemCategory.objects.all()
        }
        self.vendors: dict[str, Vendor] = {
            _norm(v.name): v for v in Vendor.objects.filter(is_deleted=False)
        }

    def category(self, name: str) -> ItemCategory:
        key = _norm(name or "Divers")
        category = self.categories.get(key)
        if category is None:
            category = ItemCategory(name=" ".join((name or "Divers").split()), created_by=self.user)
            category.save()
            self.categories[key] = category
        return category

    def item(self, values: dict[str, Any]) -> tuple[Item, bool]:
        reference = str(values.get("reference") or "").strip().upper()
        name = " ".join(str(values["name"]).split())
        item = None
        if reference:
            item = Item.objects.filter(reference__iexact=reference).first()
        item = item or Item.objects.filter(name__iexact=name).first()
        if item is not None:
            changed = []
            for key in ("rent_price", "deposit", "purchase_cost"):
                if values.get(key) is not None and getattr(item, key) != values[key]:
                    setattr(item, key, values[key])
                    changed.append(key)
            if changed:
                item.save(update_fields=[*changed, "updated_at"])
                self.report.items_updated += 1
            return item, False
        data: dict[str, Any] = {
            "name": name,
            "category": self.category(str(values.get("category") or "")),
            "reference": reference,
        }
        for key in ("rent_price", "deposit", "purchase_cost"):
            if values.get(key) is not None:
                data[key] = values[key]
        item = create_item(data, user=self.user)
        self.report.items_created += 1
        return item, True

    def own(self, values: dict[str, Any], row: int) -> None:
        item, created = self.item(values)
        quantity = values.get("quantity")
        if quantity is None:
            return
        item.refresh_from_db()
        delta = quantity - item.total_quantity
        if not delta:
            return
        if item.tracking == Item.Tracking.UNIT:
            self.report.warnings.append(
                f"ligne {row} : « {item.name} » est suivi par unité, quantité à ajuster "
                "depuis sa fiche."
            )
            return
        record_movement(
            item,
            kind=StockMovement.Kind.PURCHASE if created else StockMovement.Kind.ADJUSTMENT,
            quantity=abs(delta),
            direction=1 if delta > 0 else -1,
            reason="Import de la liste du matériel",
            user=self.user,
            create_expense=False,
        )
        self.report.stock_adjusted += 1

    def partner(self, values: dict[str, Any], row: int) -> None:
        name = " ".join(str(values.get("partner") or "").split())
        if not name:
            raise ValueError(f"ligne {row} : indiquez le nom du partenaire.")
        vendor = self.vendors.get(_norm(name))
        if vendor is None:
            vendor = Vendor.objects.create(
                name=name,
                kind=Vendor.Kind.PARTNER,
                category=Vendor.Category.RENTAL,
                phone=str(values.get("partner_phone") or "").strip()[:32],
                created_by=self.user,
            )
            self.vendors[_norm(name)] = vendor
            self.report.partners_created += 1
        elif vendor.kind != Vendor.Kind.PARTNER:
            vendor.kind = Vendor.Kind.PARTNER
            vendor.save(update_fields=["kind", "updated_at"])
        item, _ = self.item(values)
        supply = PartnerSupply.objects.filter(item=item, vendor=vendor).first()
        if supply is None:
            PartnerSupply.objects.create(
                item=item,
                vendor=vendor,
                quantity=values.get("quantity") or 0,
                unit_cost=values.get("unit_cost") or 0,
                created_by=self.user,
            )
            self.report.supplies_created += 1
            return
        if values.get("quantity") is not None:
            supply.quantity = values["quantity"]
        if values.get("unit_cost") is not None:
            supply.unit_cost = values["unit_cost"]
        supply.is_active = True
        supply.save()
        self.report.supplies_updated += 1


def run(upload: UploadedFile, *, user: User, dry_run: bool = False) -> Report:
    """All or nothing: one wrong line and nothing is saved (the report lists every error)."""
    headers, rows = read_table(upload)
    columns = _columns(headers)
    report = Report(dry_run=dry_run)
    with transaction.atomic():
        handler = _Rows(user, report)
        for offset, raw in enumerate(rows, start=2):

            def cell(key: str, raw: list[Any] = raw) -> Any:
                index = columns.get(key)
                return raw[index] if index is not None and index < len(raw) else ""

            if not str(cell("name")).strip():
                continue
            try:
                values = {
                    "name": cell("name"),
                    "category": cell("category"),
                    "reference": cell("reference"),
                    "quantity": _amount(cell("quantity"), "Quantité", offset),
                    "rent_price": _amount(cell("rent_price"), "Prix location", offset),
                    "deposit": _amount(cell("deposit"), "Caution", offset),
                    "purchase_cost": _amount(cell("purchase_cost"), "Coût achat", offset),
                    "partner": cell("partner"),
                    "partner_phone": cell("partner_phone"),
                    "unit_cost": _amount(cell("unit_cost"), "Prix partenaire", offset),
                }
                kind = _norm(cell("type"))
                is_partner = kind.startswith("part") or (
                    not kind and str(values["partner"]).strip()
                )
                with transaction.atomic():
                    if is_partner:
                        handler.partner(values, offset)
                    else:
                        handler.own(values, offset)
            except (ValueError, BusinessError) as exc:
                message = str(exc.detail) if isinstance(exc, BusinessError) else str(exc)
                if isinstance(exc, BusinessError):
                    message = f"ligne {offset} : {message}"
                report.errors.append(message)
        if dry_run or report.errors:
            transaction.set_rollback(True)
    return report


def template() -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "Matériel"
    sheet.append(TEMPLATE_HEADERS)
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4A22B5")
    for row in TEMPLATE_ROWS:
        sheet.append(row)
    for index, width in enumerate((12, 30, 16, 12, 10, 14, 10, 12, 22, 20, 16), start=1):
        sheet.column_dimensions[chr(64 + index)].width = width
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
