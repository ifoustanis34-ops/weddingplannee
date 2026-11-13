"""Reports (docs/specs/reservations-stock.md §6.5): any period, compared to the previous one,
as JSON (screen), PDF (the agency's colors and logo) or Excel.

Every report is a table — columns, rows, totals — plus a headline compared to the previous
period, so the three outputs render the same data.
"""

from __future__ import annotations

import io
from collections import defaultdict
from datetime import date
from typing import Any

from django.db.models import Sum
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone

from core.tenant import require_current_organization
from documents import palettes, rendering
from documents import services as branding_services
from documents.quote_document import long_date, money
from organizations.timezones import org_tz

from . import profitability
from .models import Expense, Revenue, RevenueCategory
from .periods import Period, last_months

TYPES = {
    "revenue": "Chiffre d’affaires par mois et par catégorie",
    "profitable": "Activités les plus rentables",
    "services": "Prestations les plus demandées",
    "items": "Articles les plus loués",
    "clients": "Clients principaux",
    "expenses": "Dépenses par catégorie",
    "margins": "Marge par événement",
    "unpaid": "Soldes impayés",
}
TOP = 15


def _col(key: str, label: str, kind: str = "text") -> dict[str, str]:
    return {"key": key, "label": label, "kind": kind}  # kind: text, money, pct, number, date


def variation(current: int, previous: int) -> float | None:
    return round((current - previous) * 100 / previous, 1) if previous else None


def _revenue_total(start: date, end: date) -> int:
    total = Revenue.objects.filter(is_cancelled=False, date__range=(start, end)).aggregate(
        t=Sum("amount")
    )["t"]
    return int(total or 0)


def _expense_total(start: date, end: date) -> int:
    return int(
        Expense.objects.filter(date__range=(start, end)).aggregate(t=Sum("amount"))["t"] or 0
    )


def _headline(label: str, current: int, previous: int) -> dict[str, Any]:
    return {
        "label": label,
        "current": current,
        "previous": previous,
        "variation_pct": variation(current, previous),
    }


# --- Builders ------------------------------------------------------------------------------------


def _revenue(period: Period) -> dict[str, Any]:
    months = [m for m in last_months(period.end, 24) if m >= period.start.replace(day=1)]
    sums: dict[date, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for revenue in Revenue.objects.filter(
        is_cancelled=False, date__range=(period.start, period.end)
    ):
        sums[revenue.date.replace(day=1)][revenue.category] += revenue.amount
    categories = RevenueCategory.choices
    rows = []
    for month in months:
        row: dict[str, Any] = {"month": month}
        for value, _ in categories:
            row[value] = sums[month][value]
        row["total"] = sum(sums[month].values())
        rows.append(row)
    totals = {value: sum(r[value] for r in rows) for value, _ in categories}
    totals["total"] = sum(totals.values())
    return {
        "columns": [_col("month", "Mois", "month")]
        + [_col(value, label, "money") for value, label in categories]
        + [_col("total", "Total", "money")],
        "rows": rows,
        "totals": totals,
        "headline": _headline(
            "Encaissé",
            totals["total"],
            _revenue_total(period.previous_start, period.previous_end),
        ),
    }


EVENT_COLUMNS = [
    _col("date", "Date", "date"),
    _col("number", "N°"),
    _col("title", "Événement"),
    _col("client", "Client"),
    _col("revenue", "Recettes", "money"),
    _col("costs", "Coûts directs", "money"),
    _col("margin", "Marge", "money"),
    _col("margin_pct", "Marge %", "pct"),
]


def _events(period: Period, *, top: bool) -> dict[str, Any]:
    rows = profitability.by_event(period)
    previous = profitability.by_event(_previous(period))
    rows = rows[:TOP] if top else sorted(rows, key=lambda r: r["date"])
    revenue = sum(r["revenue"] for r in rows)
    margin = sum(r["margin"] for r in rows)
    return {
        "columns": EVENT_COLUMNS,
        "rows": rows,
        "totals": {
            "revenue": revenue,
            "costs": sum(r["costs"] for r in rows),
            "margin": margin,
            "margin_pct": profitability.pct(margin, revenue),
        },
        "headline": _headline("Marge des événements", margin, sum(r["margin"] for r in previous)),
    }


def _previous(period: Period) -> Period:
    return Period(
        key=period.key,
        start=period.previous_start,
        end=period.previous_end,
        previous_start=period.previous_start,
        previous_end=period.previous_end,
    )


def _services(period: Period) -> dict[str, Any]:
    rows = sorted(profitability.by_service(period), key=lambda r: (-r["sales"], -r["revenue"]))
    previous = profitability.by_service(_previous(period))
    return {
        "columns": [
            _col("name", "Prestation"),
            _col("sales", "Ventes", "number"),
            _col("revenue", "Chiffre d’affaires", "money"),
            _col("margin_avg", "Marge moyenne", "pct"),
        ],
        "rows": rows[:TOP],
        "totals": {
            "sales": sum(r["sales"] for r in rows),
            "revenue": sum(r["revenue"] for r in rows),
        },
        "headline": _headline(
            "Prestations vendues",
            sum(r["sales"] for r in rows),
            sum(r["sales"] for r in previous),
        ),
    }


def _items(period: Period) -> dict[str, Any]:
    rows = [r for r in profitability.by_item(period) if r["rented_days"]]
    rows.sort(key=lambda r: r["rented_days"], reverse=True)
    previous = profitability.by_item(_previous(period))
    return {
        "columns": [
            _col("reference", "Réf."),
            _col("name", "Article"),
            _col("rented_days", "Pièces-jours louées", "number"),
            _col("utilisation_pct", "Utilisation", "pct"),
            _col("revenue", "Revenus cumulés", "money"),
            _col("payback_pct", "Rentabilisé", "pct"),
        ],
        "rows": rows[:TOP],
        "totals": {"rented_days": sum(r["rented_days"] for r in rows)},
        "headline": _headline(
            "Pièces-jours louées",
            sum(r["rented_days"] for r in rows),
            sum(r["rented_days"] for r in previous),
        ),
    }


def _by_client(start: date, end: date) -> dict[str, dict[str, Any]]:
    return {
        str(row["client"]): row
        for row in Revenue.objects.filter(
            is_cancelled=False, date__range=(start, end), client__isnull=False
        )
        .values("client", "client__name")
        .annotate(total=Sum("amount"))
    }


def _clients(period: Period) -> dict[str, Any]:
    current = _by_client(period.start, period.end)
    previous = _by_client(period.previous_start, period.previous_end)
    rows = sorted(
        (
            {
                "client": row["client__name"],
                "revenue": row["total"],
                "previous": previous.get(key, {}).get("total", 0),
                "variation_pct": variation(row["total"], previous.get(key, {}).get("total", 0)),
            }
            for key, row in current.items()
        ),
        key=lambda r: r["revenue"],
        reverse=True,
    )
    total = sum(r["revenue"] for r in rows)
    return {
        "columns": [
            _col("client", "Client"),
            _col("revenue", "Encaissé", "money"),
            _col("previous", "Période précédente", "money"),
            _col("variation_pct", "Évolution", "pct"),
        ],
        "rows": rows[:TOP],
        "totals": {"revenue": total},
        "headline": _headline(
            "Encaissé auprès des clients", total, sum(r["total"] for r in previous.values())
        ),
    }


def _by_category(start: date, end: date) -> dict[str, int]:
    return {
        row["category__name"] or "Sans catégorie": row["total"]
        for row in Expense.objects.filter(date__range=(start, end))
        .values("category__name")
        .annotate(total=Sum("amount"))
    }


def _expenses(period: Period) -> dict[str, Any]:
    current = _by_category(period.start, period.end)
    previous = _by_category(period.previous_start, period.previous_end)
    total = sum(current.values())
    rows: list[dict[str, Any]] = sorted(
        (
            {
                "category": name,
                "amount": amount,
                "share_pct": profitability.pct(amount, total),
                "previous": previous.get(name, 0),
                "variation_pct": variation(amount, previous.get(name, 0)),
            }
            for name, amount in current.items()
        ),
        key=lambda r: int(r["amount"]),
        reverse=True,
    )
    return {
        "columns": [
            _col("category", "Catégorie"),
            _col("amount", "Dépensé", "money"),
            _col("share_pct", "Part", "pct"),
            _col("previous", "Période précédente", "money"),
            _col("variation_pct", "Évolution", "pct"),
        ],
        "rows": rows,
        "totals": {"amount": total, "previous": sum(previous.values())},
        "headline": _headline("Dépensé", total, sum(previous.values())),
    }


def _unpaid(period: Period) -> dict[str, Any]:
    from contracts.models import Contract
    from reservations.commitments import SOLD
    from reservations.selectors import with_money

    from .selectors import contracts_with_metrics

    tz = org_tz(require_current_organization())
    today = timezone.now().astimezone(tz).date()
    rows: list[dict[str, Any]] = []
    for reservation in with_money().filter(status__in=SOLD, balance__gt=0):  # type: ignore[misc]
        due = timezone.localtime(reservation.event_start, tz).date()
        rows.append(
            {
                "number": reservation.number,
                "client": reservation.client.name,
                "title": reservation.title,
                "due": due,
                "balance": reservation.balance,  # type: ignore[attr-defined]
                "late_days": max(0, (today - due).days),
            }
        )
    for contract in (
        contracts_with_metrics()  # type: ignore[misc]
        .exclude(status=Contract.Status.CANCELLED)
        .filter(balance__gt=0)
    ):
        due = contract.wedding_date or today
        rows.append(
            {
                "number": contract.number,
                "client": contract.client.name,
                "title": contract.wedding.title if contract.wedding else "",
                "due": due,
                "balance": contract.balance,  # type: ignore[attr-defined]
                "late_days": max(0, (today - due).days),
            }
        )
    rows.sort(key=lambda r: (-r["late_days"], -r["balance"]))
    total = sum(r["balance"] for r in rows)
    late = sum(r["balance"] for r in rows if r["late_days"])
    return {
        "columns": [
            _col("number", "N°"),
            _col("client", "Client"),
            _col("title", "Événement"),
            _col("due", "Attendu le", "date"),
            _col("late_days", "Jours de retard", "number"),
            _col("balance", "Solde", "money"),
        ],
        "rows": rows,
        "totals": {"balance": total},
        "headline": {
            "label": "Dont en retard",
            "current": late,
            "previous": None,
            "variation_pct": None,
        },
    }


BUILDERS = {
    "revenue": _revenue,
    "profitable": lambda period: _events(period, top=True),
    "services": _services,
    "items": _items,
    "clients": _clients,
    "expenses": _expenses,
    "margins": lambda period: _events(period, top=False),
    "unpaid": _unpaid,
}


def build(kind: str, period: Period) -> dict[str, Any]:
    data = BUILDERS[kind](period)
    return {
        "type": kind,
        "title": TYPES[kind],
        "period": {
            "key": period.key,
            "start": period.start,
            "end": period.end,
            "previous_start": period.previous_start,
            "previous_end": period.previous_end,
        },
        **data,
    }


# --- Outputs -------------------------------------------------------------------------------------

MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]  # fmt: skip


def cell_text(value: Any, kind: str) -> str:
    if value is None or value == "":
        return "—"
    if kind == "money":
        return money(int(value))
    if kind == "pct":
        return f"{value:.1f}\u202f%".replace(".", ",")
    if kind == "number":
        return f"{int(value):,}".replace(",", " ")
    if kind == "date":
        return long_date(value.isoformat() if isinstance(value, date) else str(value))
    if kind == "month":
        month = value if isinstance(value, date) else date.fromisoformat(str(value))
        return f"{MONTHS[month.month - 1].capitalize()} {month.year}"
    return str(value)


def _variation_text(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:+.1f}\u202f%".replace(".", ",")


def to_pdf(report: dict[str, Any]) -> bytes:
    organization = require_current_organization()
    branding = branding_services.get_branding()
    palette = palettes.get(branding.quote_palette)
    columns = [{**c, "num": c["kind"] in ("money", "pct", "number")} for c in report["columns"]]

    def text(row: dict[str, Any], column: dict[str, Any]) -> str:
        value = row.get(column["key"])
        if column["key"] == "variation_pct":
            return _variation_text(value)
        return cell_text(value, column["kind"])

    rows = [[{"text": text(row, c), "num": c["num"]} for c in columns] for row in report["rows"]]
    totals = report.get("totals") or {}
    total_row = (
        [{"text": "Total", "num": False}]
        + [
            {"text": text(totals, c) if c["key"] in totals else "", "num": c["num"]}
            for c in columns[1:]
        ]
        if totals
        else None
    )
    headline = report.get("headline")
    html = render_to_string(
        "finance/report.html",
        {
            "report": report,
            "agency": branding.trade_name or organization.name,
            "logo": branding_services.logo_data_uri(),
            "p": palette,
            "columns": columns,
            "rows": rows,
            "total_row": total_row,
            "period": _period_text(report),
            "previous": _previous_text(report),
            "headline": (
                {
                    "label": headline["label"],
                    "current": money(headline["current"]),
                    "previous": (
                        money(headline["previous"]) if headline["previous"] is not None else None
                    ),
                    "variation": _variation_text(headline["variation_pct"]),
                }
                if headline
                else None
            ),
            "generated": long_date(
                timezone.now().astimezone(org_tz(organization)).date().isoformat()
            ),
            "fonts": {
                "m400": rendering.asset_url("fonts/montserrat-latin-400-normal.woff"),
                "m600": rendering.asset_url("fonts/montserrat-latin-600-normal.woff"),
                "m700": rendering.asset_url("fonts/montserrat-latin-700-normal.woff"),
                "p700": rendering.asset_url("fonts/playfair-display-latin-700-normal.woff"),
            },
        },
    )
    return rendering.html_to_pdf(html, str(organization.pk))


def to_xlsx(report: dict[str, Any]) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = report["title"][:31]
    sheet.append([report["title"]])
    sheet["A1"].font = Font(bold=True, size=14)
    sheet.append([_period_text(report)])
    sheet.append([])
    columns = report["columns"]
    sheet.append([c["label"] for c in columns])
    header = sheet.max_row
    for cell in sheet[header]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="17153B")

    def value(row: dict[str, Any], column: dict[str, str]) -> Any:
        raw = row.get(column["key"])
        if column["kind"] == "month" and raw is not None:
            return cell_text(raw, "month")
        return raw

    for row in report["rows"]:
        sheet.append([value(row, c) for c in columns])
    totals = report.get("totals") or {}
    if totals:
        sheet.append(["Total"] + [totals.get(c["key"]) for c in columns[1:]])
        for cell in sheet[sheet.max_row]:
            cell.font = Font(bold=True)
    for index, column in enumerate(columns, start=1):
        letter = sheet.cell(row=header, column=index).column_letter
        sheet.column_dimensions[letter].width = 34 if column["kind"] == "text" else 18
        fmt = {"money": "# ##0", "number": "# ##0", "pct": "0.0", "date": "dd/mm/yyyy"}.get(
            column["kind"]
        )
        if fmt:
            for cell in sheet[letter][header:]:
                cell.number_format = fmt
    headline = report.get("headline")
    if not headline:
        buffer = io.BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()
    sheet.append([])
    sheet.append([headline["label"], headline["current"]])
    if headline["previous"] is not None:
        sheet.append(["Période précédente", headline["previous"]])
        sheet.append(["Évolution (%)", headline["variation_pct"]])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _period_text(report: dict[str, Any]) -> str:
    period = report.get("period")
    if not period:
        return str(report.get("subtitle") or "")
    return f"Du {long_date(period['start'].isoformat())} au {long_date(period['end'].isoformat())}"


def _previous_text(report: dict[str, Any]) -> str:
    period = report.get("period")
    if not period or not period.get("previous_start"):
        return ""
    return (
        f"comparé au {long_date(period['previous_start'].isoformat())} – "
        f"{long_date(period['previous_end'].isoformat())}"
    )


def to_csv(report: dict[str, Any]) -> bytes:
    """CSV for Excel in French: « ; » separator, UTF-8 with BOM, raw numbers (no FCFA)."""
    import csv

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    columns = report["columns"]
    writer.writerow([c["label"] for c in columns])

    def raw(row: dict[str, Any], column: dict[str, str]) -> Any:
        value = row.get(column["key"])
        if value is None:
            return ""
        if column["kind"] == "month":
            return cell_text(value, "month")
        if column["kind"] == "date":
            return value.strftime("%d/%m/%Y") if hasattr(value, "strftime") else value
        if column["kind"] == "pct":
            return str(value).replace(".", ",")
        return value

    for row in report["rows"]:
        writer.writerow([raw(row, c) for c in columns])
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def respond(report: dict[str, Any], output: str, name: str) -> HttpResponse:
    """The file of a table in the format asked (pdf, xlsx, csv)."""
    content, content_type = {
        "pdf": (to_pdf, "application/pdf"),
        "xlsx": (
            to_xlsx,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
        "csv": (to_csv, "text/csv; charset=utf-8"),
    }[output]
    response = HttpResponse(content(report), content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{name}.{output}"'
    return response
