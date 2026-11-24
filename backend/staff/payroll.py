"""Pay slip computation (feedback 24/11/2026: « la paie n’est pas complète »).

A slip = gains (base, then the lines the manager adds: bonuses, allowances, overtime) − the
contributions withheld (when the agency turns them on, for people declared to the CNPS) − the
other deductions (advances, loans, absences) − what was already paid on the spot.

The Cameroon preset follows the rates in force known to us (CNPS, CGI): they are applied only
when the owner turns them on in « Réglages de la paie », and every slip says to check them with
an accountant. Amounts in francs, rounded to the franc.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

# --- Cameroon preset ----------------------------------------------------------------------------

CNPS_CEILING = 750_000  # monthly ceiling of the CNPS contributions
CNPS_EMPLOYEE = Decimal("0.042")  # old-age pension (PVID), employee share
CNPS_EMPLOYER_PENSION = Decimal("0.042")
CNPS_FAMILY = Decimal("0.07")  # family allowances, employer
CFC_EMPLOYEE = Decimal("0.01")  # Crédit Foncier
CFC_EMPLOYER = Decimal("0.015")
FNE_EMPLOYER = Decimal("0.01")  # Fonds National de l’Emploi
CAC_RATE = Decimal("0.10")  # additional council tax, on the IRPP
PROFESSIONAL_COSTS = Decimal("0.30")  # flat deduction before the IRPP
IRPP_YEARLY_ALLOWANCE = 500_000
IRPP_EXEMPT_BELOW = 62_000  # monthly gross under which no IRPP is withheld
IRPP_BRACKETS = [  # yearly taxable income → rate
    (2_000_000, Decimal("0.10")),
    (3_000_000, Decimal("0.15")),
    (5_000_000, Decimal("0.25")),
    (None, Decimal("0.35")),
]
# Redevance audiovisuelle: monthly amount by gross salary.
RAV = [
    (50_000, 0),
    (100_000, 750),
    (200_000, 1_950),
    (300_000, 3_250),
    (400_000, 4_550),
    (500_000, 5_850),
    (600_000, 7_150),
    (700_000, 8_450),
    (800_000, 9_750),
    (900_000, 11_050),
    (1_000_000, 12_350),
    (None, 13_000),
]
# Taxe de développement local: monthly amount by base salary.
TDL = [
    (62_000, 0),
    (75_000, 250),
    (100_000, 500),
    (125_000, 750),
    (150_000, 1_000),
    (200_000, 1_250),
    (250_000, 1_500),
    (300_000, 2_000),
    (500_000, 2_250),
    (None, 2_500),
]

GAIN = "gain"
DEDUCTION = "deduction"


def francs(value: Decimal | int | float) -> int:
    return int(Decimal(value).quantize(Decimal(1), ROUND_HALF_UP))


def _bracket(table: list[tuple[int | None, int]], amount: int) -> int:
    for limit, value in table:
        if limit is None or amount <= limit:
            return value
    return 0


def irpp_yearly(taxable: int) -> int:
    """Progressive scale on the yearly taxable income."""
    tax = Decimal(0)
    lower = 0
    for upper, rate in IRPP_BRACKETS:
        top = taxable if upper is None else min(taxable, upper)
        if top > lower:
            tax += (top - lower) * rate
        if upper is None or taxable <= upper:
            break
        lower = upper
    return francs(tax)


@dataclass
class Contribution:
    code: str
    label: str
    base: int
    rate: str  # « 4,2 % » or « barème »
    amount: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "label": self.label,
            "base": self.base,
            "rate": self.rate,
            "amount": self.amount,
        }


def _percent(rate: Decimal) -> str:
    return f"{(rate * 100).normalize():f}".replace(".", ",") + " %"


@dataclass
class Settings:
    enabled: bool = False
    accident_rate: Decimal = Decimal("1.75")  # % — risk group A by default
    months: Decimal = Decimal(1)  # the period, in months (ceilings and scales follow)


@dataclass
class Slip:
    base: int
    gains: list[dict[str, Any]] = field(default_factory=list)
    deductions: list[dict[str, Any]] = field(default_factory=list)
    gross: int = 0
    taxable: int = 0
    employee: list[Contribution] = field(default_factory=list)
    employer: list[Contribution] = field(default_factory=list)
    net: int = 0

    @property
    def withheld(self) -> int:
        return sum(c.amount for c in self.employee)

    @property
    def employer_total(self) -> int:
        return sum(c.amount for c in self.employer)

    @property
    def other_deductions(self) -> int:
        return sum(int(item["amount"]) for item in self.deductions)


def clean_items(raw: Any) -> list[dict[str, Any]]:
    """The lines typed by the manager: `{label, amount, kind: gain|deduction, taxable}`."""
    if not isinstance(raw, list):
        raise ValueError("Liste de lignes attendue.")
    items = []
    for entry in raw[:40]:
        if not isinstance(entry, dict):
            raise ValueError("Chaque ligne est un objet.")
        label = str(entry.get("label") or "").strip()[:80]
        try:
            amount = int(entry.get("amount") or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError("Montant illisible.") from exc
        kind = entry.get("kind") or GAIN
        if kind not in (GAIN, DEDUCTION):
            raise ValueError("Type de ligne inconnu.")
        if amount < 0:
            raise ValueError("Les montants sont positifs : choisissez « retenue » pour déduire.")
        if not label or not amount:
            continue
        items.append(
            {
                "label": label,
                "amount": amount,
                "kind": kind,
                "taxable": bool(entry.get("taxable", kind == GAIN)),
            }
        )
    return items


def compute(base: int, items: list[dict[str, Any]], *, declared: bool, settings: Settings) -> Slip:
    gains = [item for item in items if item["kind"] == GAIN]
    deductions = [item for item in items if item["kind"] == DEDUCTION]
    slip = Slip(base=base, gains=gains, deductions=deductions)
    slip.gross = base + sum(int(item["amount"]) for item in gains)
    slip.taxable = base + sum(int(item["amount"]) for item in gains if item.get("taxable", True))

    if settings.enabled and declared and slip.taxable > 0:
        months = settings.months if settings.months > 0 else Decimal(1)
        ceiling = francs(CNPS_CEILING * months)
        capped = min(slip.taxable, ceiling)
        monthly = Decimal(slip.taxable) / months

        cnps = francs(capped * CNPS_EMPLOYEE)
        slip.employee.append(
            Contribution("cnps", "CNPS — pension vieillesse", capped, _percent(CNPS_EMPLOYEE), cnps)
        )
        irpp = 0
        if monthly >= IRPP_EXEMPT_BELOW:
            yearly = (
                monthly * (1 - PROFESSIONAL_COSTS) * 12
                - Decimal(cnps) / months * 12
                - IRPP_YEARLY_ALLOWANCE
            )
            irpp = francs(Decimal(irpp_yearly(max(0, francs(yearly)))) / 12 * months)
        slip.employee.append(Contribution("irpp", "IRPP", slip.taxable, "barème", irpp))
        slip.employee.append(
            Contribution(
                "cac",
                "Centimes additionnels communaux",
                irpp,
                _percent(CAC_RATE),
                francs(irpp * CAC_RATE),
            )
        )
        slip.employee.append(
            Contribution(
                "cfc",
                "Crédit Foncier (salarié)",
                slip.taxable,
                _percent(CFC_EMPLOYEE),
                francs(slip.taxable * CFC_EMPLOYEE),
            )
        )
        slip.employee.append(
            Contribution(
                "rav",
                "Redevance audiovisuelle",
                slip.taxable,
                "barème",
                francs(_bracket(RAV, francs(monthly)) * months),
            )
        )
        slip.employee.append(
            Contribution(
                "tdl",
                "Taxe de développement local",
                base,
                "barème",
                francs(_bracket(TDL, francs(Decimal(base) / months)) * months),
            )
        )
        slip.employee = [c for c in slip.employee if c.amount or c.code in ("cnps", "irpp")]

        accident = settings.accident_rate / 100
        slip.employer = [
            Contribution(
                "cnps_pension",
                "CNPS — pension vieillesse",
                capped,
                _percent(CNPS_EMPLOYER_PENSION),
                francs(capped * CNPS_EMPLOYER_PENSION),
            ),
            Contribution(
                "cnps_family",
                "CNPS — prestations familiales",
                capped,
                _percent(CNPS_FAMILY),
                francs(capped * CNPS_FAMILY),
            ),
            Contribution(
                "cnps_accident",
                "CNPS — accidents du travail",
                capped,
                _percent(accident),
                francs(capped * accident),
            ),
            Contribution(
                "cfc_employer",
                "Crédit Foncier (employeur)",
                slip.taxable,
                _percent(CFC_EMPLOYER),
                francs(slip.taxable * CFC_EMPLOYER),
            ),
            Contribution(
                "fne",
                "Fonds National de l’Emploi",
                slip.taxable,
                _percent(FNE_EMPLOYER),
                francs(slip.taxable * FNE_EMPLOYER),
            ),
        ]

    slip.net = slip.gross - slip.withheld - slip.other_deductions
    return slip


def summary(slip: Slip) -> dict[str, Any]:
    """What a pay line keeps of its slip (shown on screen and printed)."""
    return {
        "gross": slip.gross,
        "taxable": slip.taxable,
        "employee": [c.as_dict() for c in slip.employee],
        "employer": [c.as_dict() for c in slip.employer],
        "withheld": slip.withheld,
        "employer_total": slip.employer_total,
        "other_deductions": slip.other_deductions,
        "net": slip.net,
    }
