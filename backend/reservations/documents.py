"""« Bon de sortie » and « bon de retour » (reservations-stock.md §4.1), with the agency identity.

No amounts: these sheets travel with the drivers and the storekeeper."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from documents.services import logo_data_uri

from .models import Reservation, ReservationLine

PDF_DIR = Path(settings.BASE_DIR) / "templates" / "pdf"
TITLES = {"checkout": "Bon de sortie", "return": "Bon de retour"}


def _when(value: Any) -> str:
    return timezone.localtime(value).strftime("%d/%m/%Y à %H:%M") if value else "—"


def context(reservation: Reservation, kind: str) -> dict[str, Any]:
    rows = []
    for line in reservation.lines.filter(
        kind__in=(ReservationLine.Kind.RENTAL, ReservationLine.Kind.SALE, ReservationLine.Kind.PACK)
    ).select_related("item", "pack"):
        components = (
            [
                f"{c.quantity * line.quantity} × {c.item.name}"
                for c in line.pack.components.select_related("item")
            ]
            if line.pack
            else []
        )
        rows.append(
            {
                "label": line.label,
                "reference": line.item.reference if line.item else "Pack",
                "location": line.item.location if line.item else "",
                "kind": line.get_kind_display(),
                "quantity": line.quantity,
                "out": line.quantity_out,
                "returned": line.quantity_returned,
                "damaged": line.quantity_damaged,
                "missing": line.quantity_missing,
                "components": components,
            }
        )
    return {
        "title": TITLES[kind],
        "kind": kind,
        "reservation": reservation,
        "organization": reservation.organization,
        "logo_url": logo_data_uri(),
        "client": reservation.client,
        "rows": rows,
        "dates": [
            ("Livraison", _when(reservation.delivery_at)),
            ("Installation", _when(reservation.setup_at)),
            ("Événement", f"{_when(reservation.event_start)} → {_when(reservation.event_end)}"),
            ("Récupération", _when(reservation.pickup_at)),
            ("Retour entrepôt", _when(reservation.return_at)),
        ],
        "printed_at": _when(timezone.now()),
    }


def render(reservation: Reservation, kind: str) -> bytes:
    from weasyprint import HTML

    html = render_to_string("reservations/slip.html", context(reservation, kind))
    pdf: bytes = HTML(string=html, base_url=str(PDF_DIR)).write_pdf()
    return pdf
