"""Guests and tickets (docs/specs/devis-billets.md §6, §7).

- A ticket is issued once per guest; its token is random and signed (`tokens`), only its hash
  and its random part are stored.
- « Générer » renders the ticket document (a GeneratedDocument, frozen) when it is missing or
  when the guest or the wedding's design changed since.
- Cancelling keeps the ticket (« Annulé » at the door); reissuing cancels it and issues a new
  ticket with a new token and a new number: the old QR and code no longer open the doors.
"""

from __future__ import annotations

import hashlib
import io
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any, cast
from zoneinfo import ZoneInfo

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from accounts.models import User
from core.exceptions import BusinessError
from core.tenant import require_current_organization
from documents import rendering, ticket_document
from documents import services as document_services
from documents.models import DocumentTemplate, GeneratedDocument
from events.models import Wedding

from . import tokens
from .models import Guest, Ticket, TicketDesign

KIND = DocumentTemplate.Kind.TICKET
DEFAULT_START = time(15, 0)
DESIGN_FIELDS = (
    "palette",
    "partner_1",
    "partner_2",
    "title",
    "subtitle",
    "intro",
    "panel_text",
    "bottom_slogan",
    "script_line",
    "starts_at",
    "venue",
    "address",
    "dress_code",
    "stub_title",
    "stub_subtitle",
    "stub_script",
    "stub_footer",
    "show_monogram",
    "categories",
)
GUEST_FIELDS = ("name", "email", "phone", "seats", "category", "table", "notes")


# --- Design -----------------------------------------------------------------------------------


def get_design(wedding: Wedding) -> TicketDesign:
    """The wedding's ticket design, created on first use from the wedding itself."""
    design = TicketDesign.objects.filter(wedding=wedding).first()
    if design is not None:
        return cast(TicketDesign, design)
    names = [part.strip() for part in wedding.title.replace(" et ", " & ").split("&")]
    organization = require_current_organization()
    starts_at = None
    if wedding.date:
        starts_at = datetime.combine(wedding.date, DEFAULT_START, ZoneInfo(organization.timezone))
    design, _ = TicketDesign.objects.get_or_create(
        wedding=wedding,
        defaults={
            "partner_1": names[0][:40] if names else "",
            "partner_2": names[1][:40] if len(names) > 1 else "",
            "starts_at": starts_at,
            "venue": wedding.venue[:80],
        },
    )
    return cast(TicketDesign, design)


def update_design(design: TicketDesign, data: dict[str, Any]) -> TicketDesign:
    for field in DESIGN_FIELDS:
        if field in data:
            setattr(design, field, data[field])
    design.save()
    return design


# --- Guests -----------------------------------------------------------------------------------


def create_guest(wedding: Wedding, data: dict[str, Any], *, user: User | None = None) -> Guest:
    guest = Guest(wedding=wedding, created_by=user)
    for field in GUEST_FIELDS:
        if field in data:
            setattr(guest, field, data[field])
    guest.save()
    return guest


def update_guest(guest: Guest, data: dict[str, Any]) -> Guest:
    for field in GUEST_FIELDS:
        if field in data:
            setattr(guest, field, data[field])
    guest.save()
    return guest


def delete_guest(guest: Guest) -> None:
    """A guest whose ticket was sent stays on the list: cancel the ticket instead."""
    if guest.tickets.exclude(sent_at=None).exists():
        raise BusinessError(
            "guest_has_ticket",
            "Le billet de cet invité a été envoyé : annulez-le plutôt que de supprimer l’invité.",
        )
    guest.delete()


IMPORT_COLUMNS = {
    "name": ("nom", "name", "invite", "invites", "famille", "nom complet"),
    "email": ("email", "e-mail", "mail", "courriel"),
    "phone": ("telephone", "tel", "phone", "mobile", "whatsapp"),
    "seats": ("places", "nombre de places", "seats", "personnes", "nombre"),
    "category": ("categorie", "category", "type"),
    "table": ("table",),
}
MAX_IMPORT_ROWS = 2000


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", str(text or "").strip().lower())
    return "".join(c for c in text if not unicodedata.combining(c))


@dataclass
class ImportResult:
    created: int
    skipped: list[dict[str, Any]]


@transaction.atomic
def import_guests(wedding: Wedding, upload: UploadedFile, *, user: User) -> ImportResult:
    """CSV/XLSX with a header row; columns found by name (« Nom », « Places », « Table »…)."""
    from core.spreadsheets import read_table

    headers, rows = read_table(upload)
    if len(rows) > MAX_IMPORT_ROWS:
        raise BusinessError("import_too_large", f"{MAX_IMPORT_ROWS} invités au maximum par import.")
    index: dict[str, int] = {}
    for position, header in enumerate(headers):
        key = _normalize(header)
        for field, names in IMPORT_COLUMNS.items():
            if field not in index and key in names:
                index[field] = position
    if "name" not in index:
        raise BusinessError(
            "import_no_name",
            "Ajoutez une colonne « Nom » (nom de l’invité ou de la famille).",
            {"file": ["Colonne « Nom » introuvable."]},
        )
    existing = {
        _normalize(name)
        for name in Guest.objects.filter(wedding=wedding).values_list("name", flat=True)
    }
    created, skipped = 0, []

    def cell(row: list[Any], field: str) -> str:
        position = index.get(field)
        value = row[position] if position is not None and position < len(row) else ""
        return str(value or "").strip()

    for number, row in enumerate(rows, start=2):
        name = cell(row, "name")
        if not name:
            continue
        if _normalize(name) in existing:
            skipped.append({"row": number, "name": name, "reason": "Déjà dans la liste"})
            continue
        try:
            seats = max(1, min(50, int(float(cell(row, "seats") or 1))))
        except ValueError:
            seats = 1
        create_guest(
            wedding,
            {
                "name": name[:120],
                "email": cell(row, "email")[:254],
                "phone": cell(row, "phone")[:32],
                "seats": seats,
                "category": cell(row, "category")[:30],
                "table": cell(row, "table")[:30],
            },
            user=user,
        )
        existing.add(_normalize(name))
        created += 1
    return ImportResult(created=created, skipped=skipped)


# --- Tickets ----------------------------------------------------------------------------------


def _next_number(wedding: Wedding) -> int:
    # Lock the wedding row: two simultaneous issues never take the same number.
    Wedding.objects.select_for_update().filter(pk=wedding.pk).first()
    current = Ticket.objects.filter(wedding=wedding).aggregate(top=Max("number"))["top"]
    return (current or 0) + 1


@transaction.atomic
def issue_ticket(guest: Guest, *, user: User | None = None) -> Ticket:
    """The guest's active ticket, issued if they have none (signed token, readable code)."""
    current = guest.tickets.filter(status=Ticket.Status.ACTIVE).first()
    if current is not None:
        return current
    organization = require_current_organization()
    design = get_design(guest.wedding)
    number = _next_number(guest.wedding)
    token, token_id = tokens.new_token(organization.pk)
    ticket = Ticket.objects.create(
        wedding=guest.wedding,
        guest=guest,
        token_id=token_id,
        token_hash=tokens.token_hash(token),
        number=number,
        code=f"WDV-{ticket_document.initials(design, guest.wedding.title)}-{number:04d}",
        created_by=user,
    )
    return cast(Ticket, ticket)


def token(ticket: Ticket) -> str:
    return tokens.token_for(ticket.organization_id, ticket.token_id)


def public_url(ticket: Ticket) -> str:
    return ticket_document.ticket_url(ticket.organization.slug, token(ticket))


def _agency() -> dict[str, Any]:
    branding = document_services.get_branding()
    return {
        "trade_name": branding.trade_name or branding.organization.name,
        "logo": branding.logo.name or None,
    }


def ticket_snapshot(ticket: Ticket) -> dict[str, Any]:
    organization = require_current_organization()
    guest = ticket.guest
    return ticket_document.build_snapshot(
        organization_id=str(organization.pk),
        slug=organization.slug,
        timezone=organization.timezone,
        design=get_design(ticket.wedding),
        agency=_agency(),
        guest={
            "name": guest.name,
            "seats": guest.seats,
            "category": guest.category,
            "table": guest.table,
        },
        ticket={"code": ticket.code, "token_id": ticket.token_id},
        status=ticket.status,
    )


def preview_snapshot(wedding: Wedding, design: Any) -> dict[str, Any]:
    """The design form's preview: an example guest, a placeholder QR (§6 « aperçu PNG »)."""
    organization = require_current_organization()
    return ticket_document.build_snapshot(
        organization_id=str(organization.pk),
        slug=organization.slug,
        timezone=organization.timezone,
        design=design,
        agency=_agency(),
        guest=dict(ticket_document.PREVIEW_GUEST),
        # The code the first ticket will get; no token: the QR of the preview opens nothing.
        ticket={
            "code": f"WDV-{ticket_document.initials(design, wedding.title)}-0001",
            "token_id": None,
        },
    )


def render(snapshot: dict[str, Any]) -> rendering.Rendering:
    return rendering.render(
        ticket_document.TEMPLATE, ticket_document.context(snapshot), snapshot["organization_id"]
    )


def render_pdf(snapshot: dict[str, Any]) -> bytes:
    """PDF only: the image is derived from it when needed (batches stay fast, §6)."""
    from django.template.loader import render_to_string

    html = render_to_string(ticket_document.TEMPLATE, ticket_document.context(snapshot))
    return rendering.html_to_pdf(html, snapshot["organization_id"])


@transaction.atomic
def generate(ticket: Ticket) -> GeneratedDocument:
    """The ticket's document, re-rendered only when what it shows changed."""
    snapshot = ticket_snapshot(ticket)
    fingerprint = rendering.fingerprint(snapshot)
    current = ticket.document
    if current is not None and rendering.fingerprint(current.data_snapshot) == fingerprint:
        return current
    template, _ = DocumentTemplate.objects.get_or_create(
        kind=KIND,
        code="ticket",
        version=1,
        defaults={
            "name": "Ticket détachable",
            "path": ticket_document.TEMPLATE,
            "page_size": "200x118mm",
            "is_default": True,
        },
    )
    pdf = render_pdf(snapshot)
    version = (
        GeneratedDocument.objects.filter(kind=KIND, object_id=ticket.pk).aggregate(
            v=Max("version")
        )["v"]
        or 0
    ) + 1
    document = GeneratedDocument(
        organization=require_current_organization(),
        kind=KIND,
        object_id=ticket.pk,
        version=version,
        template=template,
        data_snapshot=snapshot,
        sha256=hashlib.sha256(pdf).hexdigest(),
    )
    document.pdf_file.save(f"{ticket.code}.pdf", ContentFile(pdf), save=False)
    document.save()
    ticket.document = document
    ticket.save(update_fields=["document", "updated_at"])
    return document


def pdf_bytes(ticket: Ticket) -> bytes:
    document = generate(ticket)
    with document.pdf_file.open("rb") as handle:
        content: bytes = handle.read()
    return content


def image(ticket: Ticket) -> bytes:
    """PNG of the ticket (public page, email): derived from the frozen PDF, then kept."""
    document = generate(ticket)
    if not document.png_file:
        with document.pdf_file.open("rb") as handle:
            png = rendering.pdf_to_pngs(handle.read())[0]
        document.png_file.save(f"{ticket.code}.png", ContentFile(png), save=False)
        document.save(update_fields=["png_file", "updated_at"])
    with document.png_file.open("rb") as handle:
        content: bytes = handle.read()
    return content


@transaction.atomic
def cancel_ticket(ticket: Ticket) -> Ticket:
    if ticket.status != Ticket.Status.ACTIVE:
        raise BusinessError("ticket_not_active", "Ce billet est déjà annulé.")
    ticket.status = Ticket.Status.CANCELLED
    ticket.cancelled_at = timezone.now()
    ticket.save(update_fields=["status", "cancelled_at", "updated_at"])
    return ticket


@transaction.atomic
def reissue_ticket(ticket: Ticket, *, user: User | None = None) -> Ticket:
    """New token, new number: the old QR answers « Annulé » at the door (§7)."""
    if ticket.status == Ticket.Status.ACTIVE:
        ticket.status = Ticket.Status.REISSUED
        ticket.cancelled_at = timezone.now()
        ticket.save(update_fields=["status", "cancelled_at", "updated_at"])
    elif ticket.guest.tickets.filter(status=Ticket.Status.ACTIVE).exists():
        raise BusinessError("ticket_already_reissued", "Cet invité a déjà un billet actif.")
    fresh = issue_ticket(ticket.guest, user=user)
    generate(fresh)
    return fresh


# --- Exports ----------------------------------------------------------------------------------


def export_pdf(tickets: list[Ticket]) -> bytes:
    """One PDF with a page per ticket."""
    import pypdfium2 as pdfium

    merged = pdfium.PdfDocument.new()
    try:
        for ticket in tickets:
            source = pdfium.PdfDocument(pdf_bytes(ticket))
            merged.import_pages(source)
            source.close()
        out = io.BytesIO()
        merged.save(out)
        return out.getvalue()
    finally:
        merged.close()


def export_zip(tickets: list[Ticket]) -> bytes:
    """One PDF per guest (« WDV-DG-0001 - Famille Kouassi.pdf »)."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for ticket in tickets:
            safe = "".join(c for c in ticket.guest.name if c.isalnum() or c in " -_'’").strip()
            archive.writestr(f"{ticket.code} - {safe or 'invite'}.pdf", pdf_bytes(ticket))
    return out.getvalue()


# --- Public page ------------------------------------------------------------------------------


def find_by_token(token_value: str) -> Ticket | None:
    """Across organizations: the random part finds the ticket, the signature proves it."""
    from core.tenant import bypass_tenant

    parsed = tokens.parse(token_value)
    if parsed is None:
        return None
    with bypass_tenant():
        ticket = (
            Ticket.all_tenants.select_related("organization", "guest", "wedding")
            .filter(token_id=parsed.ticket_id_hex, organization__is_active=True)
            .first()
        )
    if ticket is None or not tokens.verify(ticket.organization_id, parsed):
        return None
    return cast(Ticket, ticket)


def mark_opened(ticket: Ticket) -> None:
    if ticket.opened_at is None:
        ticket.opened_at = timezone.now()
        ticket.save(update_fields=["opened_at", "updated_at"])


@transaction.atomic
def answer_rsvp(ticket: Ticket, accepted: bool) -> Guest:
    """The guest confirms or declines from their page. Never records an entry (§6)."""
    if ticket.status != Ticket.Status.ACTIVE:
        raise BusinessError("ticket_cancelled", "Ce billet a été annulé.")
    guest = ticket.guest
    guest.rsvp_status = Guest.Rsvp.ACCEPTED if accepted else Guest.Rsvp.DECLINED
    guest.rsvp_at = timezone.now()
    guest.save(update_fields=["rsvp_status", "rsvp_at", "updated_at"])
    return guest


def ics(ticket: Ticket) -> str:
    """Calendar file of the wedding (6 hours from the start time by default)."""
    design = get_design(ticket.wedding)
    names = " & ".join(n for n in (design.partner_1, design.partner_2) if n)

    def escape(text: str) -> str:
        return (
            text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
        )

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Wedivo//Billets//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{ticket.pk}@wedivo.app",
        f"DTSTAMP:{timezone.now().strftime('%Y%m%dT%H%M%SZ')}",
    ]
    if design.starts_at:
        start = design.starts_at.astimezone(ZoneInfo("UTC"))
        end = start + timedelta(hours=6)
        lines += [f"DTSTART:{start:%Y%m%dT%H%M%SZ}", f"DTEND:{end:%Y%m%dT%H%M%SZ}"]
    elif ticket.wedding.date:
        day = ticket.wedding.date
        lines += [f"DTSTART;VALUE=DATE:{day:%Y%m%d}"]
    location = ", ".join(part for part in (design.venue, design.address) if part)
    lines += [
        f"SUMMARY:{escape(f'Mariage de {names}' if names else ticket.wedding.title)}",
        f"LOCATION:{escape(location)}" if location else "",
        f"DESCRIPTION:{escape(f'Billet {ticket.code} · {ticket.guest.name}')}",
        f"URL:{public_url(ticket)}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(line for line in lines if line) + "\r\n"
