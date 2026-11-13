"""Printable QR labels of the equipment (reservations-stock.md §5.3): A4 sheets of 3 × 8 labels.

The QR holds ``WDV1:ITEM:<reference>`` (or ``WDV1:UNIT:<reference>:<serial>``), read by the scan
screen in « Sortie » / « Retour » mode (step S4)."""

from __future__ import annotations

from django.template.loader import render_to_string

from core.tenant import require_current_organization
from documents import qr, rendering

from .models import Item


def payload(item: Item, serial: str | None = None) -> str:
    return f"WDV1:UNIT:{item.reference}:{serial}" if serial else f"WDV1:ITEM:{item.reference}"


def render(items: list[Item], *, copies: int = 1) -> bytes:
    organization = require_current_organization()
    labels = []
    for item in items:
        units = list(item.units.exclude(status__in=["sold", "lost"]))
        if item.tracking == Item.Tracking.UNIT and units:
            for unit in units:
                labels.append(
                    {
                        "name": item.name,
                        "reference": item.reference,
                        "serial": unit.serial_number,
                        "qr": qr.svg(payload(item, unit.serial_number)),
                    }
                )
        else:
            code = qr.svg(payload(item))
            labels.extend(
                {"name": item.name, "reference": item.reference, "serial": "", "qr": code}
                for _ in range(copies)
            )
    html = render_to_string(
        "stock/labels.html", {"labels": labels, "organization": organization.name}
    )
    return rendering.html_to_pdf(html, str(organization.pk))
