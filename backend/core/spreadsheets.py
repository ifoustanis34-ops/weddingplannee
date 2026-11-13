"""Reading of uploaded CSV / XLSX tables (guest import, later stock import)."""

from __future__ import annotations

import csv
import io
from typing import Any

from django.core.files.uploadedfile import UploadedFile

from .exceptions import BusinessError

MAX_ROWS = 2000
MAX_BYTES = 5 * 1024 * 1024


def _read_csv(raw: bytes) -> list[list[str]]:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover - cp1252 decodes nearly everything
        raise BusinessError("import_unreadable", "Encodage du fichier non reconnu.")
    try:
        dialect: Any = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return [row for row in csv.reader(io.StringIO(text), dialect) if any(c.strip() for c in row)]


def _read_xlsx(raw: bytes) -> list[list[Any]]:
    from openpyxl import load_workbook

    try:
        workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    except Exception as exc:
        raise BusinessError(
            "import_unreadable",
            "Ce fichier Excel est illisible. Enregistrez-le à nouveau en .xlsx.",
        ) from exc
    sheet = workbook.worksheets[0]
    rows = [
        ["" if cell is None else cell for cell in row]
        for row in sheet.iter_rows(values_only=True)
        if any(cell not in (None, "") for cell in row)
    ]
    workbook.close()
    return rows


def read_table(upload: UploadedFile) -> tuple[list[str], list[list[Any]]]:
    if upload.size and upload.size > MAX_BYTES:
        raise BusinessError("import_too_large", "Fichier trop lourd : 5 Mo maximum.")
    name = (upload.name or "").lower()
    raw = upload.read()
    if name.endswith(".csv"):
        rows: list[list[Any]] = list(_read_csv(raw))
    elif name.endswith(".xlsx"):
        rows = _read_xlsx(raw)
    else:
        raise BusinessError(
            "import_format", "Format non pris en charge. Importez un fichier .csv ou .xlsx."
        )
    if len(rows) < 2:
        raise BusinessError(
            "import_empty", "Le fichier doit contenir une ligne de titres et au moins une ligne."
        )
    if len(rows) - 1 > MAX_ROWS:
        raise BusinessError("import_too_many_rows", f"{MAX_ROWS} lignes maximum par import.")
    headers = [str(cell).strip() or f"Colonne {index + 1}" for index, cell in enumerate(rows[0])]
    return headers, rows[1:]
