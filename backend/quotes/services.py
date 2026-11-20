"""Quote lifecycle (CLAUDE.md §7.3): edit → send → accept / refuse / expire → contract."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from catalog.models import ServiceItem
from contracts.models import Contract, PaymentSchedule
from core import audit
from core.exceptions import BusinessError
from core.tenant import require_current_organization
from crm import services as crm_services
from crm.models import Client
from events.models import Wedding
from organizations.models import DocumentSequence
from organizations.numbering import next_number

from .calculations import compute_totals, line_amount
from .models import Quote, QuoteLine, QuotePartner

EDITABLE_STATUSES = {Quote.Status.DRAFT, Quote.Status.SENT, Quote.Status.EXPIRED}
DEFAULT_TERMS = (
    "Acompte à la signature du contrat. Solde 7 jours avant le mariage. "
    "Paiement par virement, Mobile Money ou espèces."
)
BALANCE_DAYS_BEFORE_WEDDING = 7


@dataclass(frozen=True)
class LineInput:
    label: str
    unit: str
    unit_price: int
    quantity: Decimal
    description: str = ""
    service_item: ServiceItem | None = None
    icon: str = ""


def public_url(quote: Quote) -> str:
    return f"{settings.FRONTEND_URL}/proposition/{quote.public_token}"


# --- Editing -------------------------------------------------------------------------------


def _apply_lines(quote: Quote, lines: Iterable[LineInput], user: User) -> None:
    quote.lines.all().delete()
    amounts: list[int] = []
    for position, line in enumerate(lines):
        amount = line_amount(line.unit_price, line.quantity)
        amounts.append(amount)
        QuoteLine.objects.create(
            quote=quote,
            service_item=line.service_item,
            label=line.label.strip(),
            description=line.description.strip(),
            unit=line.unit,
            unit_price=line.unit_price,
            quantity=line.quantity,
            amount=amount,
            position=position,
            icon=line.icon,
            created_by=user,
        )
    totals = compute_totals(amounts, quote.discount_pct, quote.deposit_pct)
    quote.subtotal = totals.subtotal
    quote.discount_amount = totals.discount_amount
    quote.total = totals.total
    quote.deposit_amount = totals.deposit_amount


QUOTE_FIELDS = (
    "client",
    "issue_date",
    "valid_until",
    "wedding_date",
    "guest_count",
    "discount_pct",
    "deposit_pct",
    "payment_terms",
    "notes",
    "template_name",
    # Document (docs/specs/devis-billets.md §2f)
    "design",
    "palette",
    "tagline",
    "event_type",
    "venue",
)
PARTNER_FIELDS = ("name", "activity", "signatory", "signatory_role")
MAX_PARTNERS = 2


def _apply_partners(quote: Quote, partners: Iterable[dict[str, Any]], user: User) -> None:
    """External partners « En partenariat avec … » (§2d), replaced as a whole like the lines."""
    quote.partners.all().delete()
    for position, partner in enumerate(list(partners)[:MAX_PARTNERS]):
        QuotePartner.objects.create(
            quote=quote,
            position=position,
            created_by=user,
            **{field: str(partner.get(field, "")).strip() for field in PARTNER_FIELDS},
        )


def default_dates() -> tuple[date, date]:
    """Issue date and validity of a new quote (today + the agency's validity)."""
    today = timezone.localdate()
    return today, today + timedelta(days=require_current_organization().quote_validity_days)


@transaction.atomic
def create_quote(data: dict[str, Any], lines: list[LineInput], *, user: User) -> Quote:
    organization = require_current_organization()
    today = timezone.localdate()
    is_template = bool(data.get("is_template"))
    client: Client | None = data.get("client")
    if not is_template and client is None:
        raise BusinessError(
            "invalid", "Choisissez le client du devis.", {"client": ["Client obligatoire."]}
        )
    quote = Quote(
        created_by=user,
        is_template=is_template,
        issue_date=today,
        valid_until=today + timedelta(days=organization.quote_validity_days),
        payment_terms=DEFAULT_TERMS,
        number="" if is_template else next_number(DocumentSequence.Kind.QUOTE),
    )
    for field in QUOTE_FIELDS:
        if field in data:
            setattr(quote, field, data[field])
    quote.save()
    _apply_lines(quote, lines, user)
    if data.get("partners"):
        _apply_partners(quote, data["partners"], user)
    quote.save()
    return quote


@transaction.atomic
def update_quote(
    quote: Quote, data: dict[str, Any], lines: list[LineInput] | None, *, user: User
) -> Quote:
    if quote.status not in EDITABLE_STATUSES:
        raise BusinessError(
            "quote_locked",
            "Ce devis est déjà accepté ou refusé : dupliquez-le pour le modifier.",
        )
    for field in QUOTE_FIELDS:
        if field in data:
            setattr(quote, field, data[field])
    if lines is None:
        lines = [
            LineInput(
                label=line.label,
                unit=line.unit,
                unit_price=line.unit_price,
                quantity=line.quantity,
                description=line.description,
                service_item=line.service_item,
                icon=line.icon,
            )
            for line in quote.lines.all()
        ]
    _apply_lines(quote, lines, user)
    if "partners" in data:
        _apply_partners(quote, data["partners"], user)
    if quote.status == Quote.Status.EXPIRED and quote.valid_until >= timezone.localdate():
        quote.status = Quote.Status.SENT if quote.sent_at else Quote.Status.DRAFT
    quote.save()
    return quote


@transaction.atomic
def duplicate_quote(
    source: Quote, *, user: User, as_template: bool = False, client: Client | None = None
) -> Quote:
    """Copy of a quote, or a quote from a template (``client`` required then)."""
    lines = [
        LineInput(
            label=line.label,
            unit=line.unit,
            unit_price=line.unit_price,
            quantity=line.quantity,
            description=line.description,
            service_item=line.service_item,
            icon=line.icon,
        )
        for line in source.lines.all()
    ]
    data: dict[str, Any] = {
        "is_template": as_template,
        "client": None if as_template else (client or source.client),
        "discount_pct": source.discount_pct,
        "deposit_pct": source.deposit_pct,
        "payment_terms": source.payment_terms,
        "notes": source.notes,
        "template_name": source.template_name if as_template else "",
        "design": source.design,
        "palette": source.palette,
        "tagline": source.tagline,
        "event_type": source.event_type,
        "venue": source.venue,
        "partners": [
            {field: getattr(partner, field) for field in PARTNER_FIELDS}
            for partner in source.partners.all()
        ],
    }
    if not as_template and client is None and source.client is not None:
        data["wedding_date"] = source.wedding_date
        data["guest_count"] = source.guest_count
    if as_template and not data["template_name"]:
        data["template_name"] = f"Modèle — {source.number or 'devis'}"
    return create_quote(data, lines, user=user)


# --- Sending -------------------------------------------------------------------------------


@transaction.atomic
def send_quote(quote: Quote, *, user: User, channel: str = "email") -> Quote:
    """Mark as sent, then generate the PDF and email it in Celery (queues ``pdf``, ``emails``).

    ``channel="whatsapp"`` (feedback 20/11/2026): the planner sends the public link from their own
    WhatsApp (manual message, never sent by Wedivo). The quote is marked as sent and its version is
    frozen, without email: neither the client's email nor a verified sender is required."""
    from .tasks import deliver_quote

    if quote.is_template:
        raise BusinessError(
            "invalid", "Un modèle ne s’envoie pas : créez un devis à partir de lui."
        )
    if quote.status not in EDITABLE_STATUSES:
        raise BusinessError("quote_locked", "Ce devis est déjà accepté ou refusé.")
    by_email = channel != "whatsapp"
    if by_email and not user.is_verified:
        raise BusinessError(
            "email_not_verified",
            "Confirmez votre adresse email avant d’envoyer des devis (lien reçu à l’inscription).",
            status_code=403,
        )
    assert quote.client is not None
    if by_email and not quote.client.email:
        raise BusinessError(
            "client_email_missing",
            "Ajoutez l’email du client dans sa fiche pour lui envoyer le devis.",
        )
    if not quote.lines.exists():
        raise BusinessError("quote_empty", "Ajoutez au moins une prestation avant l’envoi.")
    if quote.valid_until < timezone.localdate():
        raise BusinessError(
            "quote_expired",
            "La date de validité est dépassée : repoussez-la avant d’envoyer.",
            {"valid_until": ["Date passée."]},
        )

    quote.status = Quote.Status.SENT
    quote.sent_at = timezone.now()
    quote.save(update_fields=["status", "sent_at", "updated_at"])

    organization = require_current_organization()
    transaction.on_commit(
        lambda: deliver_quote.delay(
            str(organization.pk), str(quote.pk), str(user.pk), email=by_email
        )
    )
    return quote


# --- Decision ------------------------------------------------------------------------------


def _check_open(quote: Quote) -> None:
    if quote.status not in (Quote.Status.SENT, Quote.Status.DRAFT):
        label = Quote.Status(quote.status).label.lower()
        raise BusinessError("quote_closed", f"Ce devis est déjà {label}.")
    if quote.valid_until < timezone.localdate():
        raise BusinessError(
            "quote_expired", "Ce devis a expiré. Demandez une nouvelle proposition à l’agence."
        )


@transaction.atomic
def accept_quote(quote: Quote, *, user: User | None, online: bool = False) -> Quote:
    _check_open(quote)
    quote.status = Quote.Status.ACCEPTED
    quote.accepted_at = timezone.now()
    quote.save(update_fields=["status", "accepted_at", "updated_at"])
    if online:  # the client answered on the public page: the managers hear it at once
        from notifications import flow

        flow.quote_answer(quote, accepted=True)
    return quote


@transaction.atomic
def refuse_quote(
    quote: Quote, *, user: User | None, reason: str = "", online: bool = False
) -> Quote:
    _check_open(quote)
    quote.status = Quote.Status.REFUSED
    quote.refused_at = timezone.now()
    quote.refusal_reason = reason.strip()
    quote.save(update_fields=["status", "refused_at", "refusal_reason", "updated_at"])
    if online:
        from notifications import flow

        flow.quote_answer(quote, accepted=False)
    return quote


# --- Conversion ----------------------------------------------------------------------------


def _balance_due_date(wedding_date: date | None, today: date) -> date:
    if wedding_date is None:
        return today + timedelta(days=30)
    return max(today, wedding_date - timedelta(days=BALANCE_DAYS_BEFORE_WEDDING))


@transaction.atomic
def convert_to_contract(quote: Quote, *, user: User, request: Any = None) -> Contract:
    """Accepted quote → contract, payment schedule and wedding record; client unarchived."""
    if quote.status != Quote.Status.ACCEPTED:
        raise BusinessError("quote_not_accepted", "Seul un devis accepté peut devenir un contrat.")
    if Contract.objects.filter(quote=quote).exists():
        raise BusinessError("already_converted", "Ce devis a déjà été converti en contrat.")
    assert quote.client is not None
    client = quote.client
    today = timezone.localdate()

    contract: Contract = Contract.objects.create(
        number=next_number(DocumentSequence.Kind.CONTRACT),
        quote=quote,
        client=client,
        total=quote.total,
        signed_at=timezone.now(),
        wedding_date=quote.wedding_date,
        created_by=user,
    )
    position = 0
    if quote.deposit_amount > 0:
        PaymentSchedule.objects.create(
            contract=contract,
            label="Acompte",
            amount=quote.deposit_amount,
            due_date=today,
            position=position,
            created_by=user,
        )
        position += 1
    balance = quote.total - quote.deposit_amount
    if balance > 0:
        PaymentSchedule.objects.create(
            contract=contract,
            label="Solde",
            amount=balance,
            due_date=_balance_due_date(quote.wedding_date, today),
            position=position,
            created_by=user,
        )
    Wedding.objects.create(
        title=client.name,
        date=quote.wedding_date,
        guest_count=quote.guest_count,
        budget=quote.total,
        contract=contract,
        client=client,
        created_by=user,
    )
    crm_services.ensure_active(client)
    audit.record(
        "contract.created",
        contract,
        request=request,
        changes={"quote": quote.number, "total": quote.total},
    )
    return contract


def expire_overdue_quotes(today: date | None = None) -> int:
    """Sent quotes past their validity become « Expiré » (daily task, all organizations)."""
    today = today or timezone.localdate()
    return Quote.all_tenants.filter(status=Quote.Status.SENT, valid_until__lt=today).update(
        status=Quote.Status.EXPIRED, updated_at=timezone.now()
    )
