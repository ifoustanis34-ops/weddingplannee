from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage

from core.tenant import tenant_context_for_id

from . import pdf
from .models import Payment
from .services import money

RETRY = {"autoretry_for": (Exception,), "retry_backoff": True, "max_retries": 3}


@shared_task(queue="pdf", **RETRY)  # type: ignore[untyped-decorator]
def send_receipt(organization_id: str, payment_id: str) -> None:
    """Generate the receipt PDF and email it to the client (when an address is known)."""
    with tenant_context_for_id(organization_id) as organization:
        payment = (
            Payment.objects.select_related("contract__client", "recorded_by")
            .filter(pk=payment_id, is_cancelled=False)
            .first()
        )
        if payment is None:
            return
        content = pdf.render_pdf(payment)
        if not payment.receipt_file:
            payment.receipt_file.save(pdf.filename(payment), ContentFile(content), save=False)
            payment.save(update_fields=["receipt_file", "updated_at"])
        client = payment.contract.client
        if not client.email:
            return
        message = EmailMessage(
            subject=f"Reçu {payment.receipt_number} — {organization.name}",
            body=(
                f"Bonjour {client.name},\n\n"
                f"Nous confirmons la réception de {money(payment.amount)} "
                f"pour le contrat {payment.contract.number}. Votre reçu est joint.\n\n"
                f"Merci pour votre confiance,\n{organization.name}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[client.email],
            reply_to=[payment.recorded_by.email] if payment.recorded_by else None,
        )
        message.attach(pdf.filename(payment), content, "application/pdf")
        message.send()
