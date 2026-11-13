"""Payment receipt PDF (WeasyPrint), same visual language as quotes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.conf import settings
from django.template.loader import render_to_string

from documents.services import logo_data_uri
from quotes.pdf import french_date

from .models import Payment
from .services import allocate, collected, money

PDF_DIR = Path(settings.BASE_DIR) / "templates" / "pdf"


def context(payment: Payment) -> dict[str, Any]:
    contract = payment.contract
    organization = contract.organization
    paid_total = collected(contract)
    return {
        "payment": payment,
        "organization": organization,
        "logo_url": logo_data_uri(),
        "contract": contract,
        "client": contract.client,
        "amount": money(payment.amount),
        "method": payment.get_method_display(),
        "paid_at": french_date(payment.paid_at),
        "contract_total": money(contract.total),
        "collected": money(paid_total),
        "balance": money(contract.total - paid_total),
        "wedding_date": french_date(contract.wedding_date),
        "schedule": [
            {
                "label": allocation.schedule.label,
                "due_date": french_date(allocation.schedule.due_date),
                "amount": money(allocation.schedule.amount),
                "status": (
                    "Payé"
                    if allocation.remaining == 0
                    else (f"Reste {money(allocation.remaining)}" if allocation.paid else "À venir")
                ),
            }
            for allocation in allocate(contract)
        ],
    }


def render_pdf(payment: Payment) -> bytes:
    from weasyprint import HTML

    html = render_to_string("pdf/receipt.html", context(payment))
    pdf: bytes = HTML(string=html, base_url=str(PDF_DIR)).write_pdf()
    return pdf


def filename(payment: Payment) -> str:
    return f"{payment.receipt_number or 'recu'}.pdf"
