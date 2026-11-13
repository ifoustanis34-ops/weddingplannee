"""Contracts export (CSV for any spreadsheet, XLSX for Excel). Traced in the audit log."""

from __future__ import annotations

import csv
import io
from typing import Any

from contracts.models import Contract

from .selectors import contracts_with_metrics

HEADERS = [
    "Numéro",
    "Client",
    "Date du mariage",
    "Statut",
    "Montant du contrat (FCFA)",
    "Encaissé (FCFA)",
    "Solde (FCFA)",
    "Dépenses estimées (FCFA)",
    "Marge prévisionnelle (FCFA)",
]


def rows() -> list[list[Any]]:
    return [
        [
            c.number,
            c.client.name,
            c.wedding_date.isoformat() if c.wedding_date else "",
            c.get_status_display(),
            c.total,
            c.collected,  # type: ignore[attr-defined]
            c.balance,  # type: ignore[attr-defined]
            c.expenses,  # type: ignore[attr-defined]
            c.margin,  # type: ignore[attr-defined]
        ]
        for c in contracts_with_metrics()
        .exclude(status=Contract.Status.CANCELLED)
        .order_by("wedding_date")
    ]


def to_csv() -> bytes:
    buffer = io.StringIO()
    # Semicolon + BOM: opens directly in Excel configured in French.
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(HEADERS)
    writer.writerows(rows())
    return ("﻿" + buffer.getvalue()).encode("utf-8")


def to_xlsx() -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "Contrats"
    sheet.append(HEADERS)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for row in rows():
        sheet.append(row)
    for column in "EFGHI":
        for cell in sheet[column][1:]:
            cell.number_format = "# ##0"
    for index, width in enumerate([14, 28, 16, 12, 22, 18, 18, 22, 24]):
        sheet.column_dimensions[chr(65 + index)].width = width
    sheet.append([])
    sheet.append(["La marge prévisionnelle n’est pas le bénéfice net comptable de l’entreprise."])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
