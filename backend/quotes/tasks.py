from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage

from accounts.models import User
from core.tenant import tenant_context_for_id
from documents import generation

from . import pdf
from .models import Quote
from .services import expire_overdue_quotes, public_url

RETRY = {"autoretry_for": (Exception,), "retry_backoff": True, "max_retries": 3}


@shared_task(queue="pdf", **RETRY)  # type: ignore[untyped-decorator]
def deliver_quote(organization_id: str, quote_id: str, sender_id: str, email: bool = True) -> None:
    """Generate the PDF of the sent version, then email it with the public link (``email``:
    false when the planner sent the link by WhatsApp)."""
    with tenant_context_for_id(organization_id) as organization:
        quote = Quote.objects.select_related("client").filter(pk=quote_id).first()
        if quote is None:
            return
        # The sent version is frozen (snapshot, PDF, PNG): never regenerated in silence.
        document = generation.generate(quote)
        if not email or quote.client is None or not quote.client.email:
            return
        content = generation.pdf_bytes(document)
        sender = User.objects.filter(pk=sender_id).first()

        message = EmailMessage(
            subject=f"Votre devis {quote.number} — {organization.name}",
            body=(
                f"Bonjour {quote.client.name},\n\n"
                f"Vous trouverez ci-joint notre devis {quote.number} d’un montant de "
                f"{pdf.money(quote.total)}.\n\n"
                f"Consultez-le et donnez votre réponse en ligne :\n{public_url(quote)}\n\n"
                f"Ce devis est valable jusqu’au {pdf.french_date(quote.valid_until)}.\n\n"
                f"Bien cordialement,\n{sender.full_name if sender else ''}\n{organization.name}"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[quote.client.email],
            reply_to=[sender.email] if sender else None,
        )
        message.attach(generation.filename(quote), content, "application/pdf")
        message.send()


@shared_task(queue="default")  # type: ignore[untyped-decorator]
def expire_quotes() -> int:
    """Daily (beat): sent quotes past their validity date become « Expiré »."""
    from core.tenant import bypass_tenant

    with bypass_tenant():
        return expire_overdue_quotes()
