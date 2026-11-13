"""Guests and tickets (docs/specs/devis-billets.md §6, §7, §11, §12)."""

from __future__ import annotations

import io
import uuid
import zipfile
from collections.abc import Callable
from datetime import date
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import Membership, User
from core.tenant import tenant_context
from documents import barcodes
from events.models import Wedding
from invitations import services, tokens
from invitations.models import Guest, Ticket
from organizations.models import Organization

pytestmark = pytest.mark.django_db
zxingcpp = pytest.importorskip("zxingcpp")


@pytest.fixture
def client(client_for: Callable[..., APIClient], owner_a: User, org_a: Organization) -> APIClient:
    return client_for(owner_a, org_a)


@pytest.fixture
def wedding(org_a: Organization) -> Wedding:
    with tenant_context(org_a):
        created: Wedding = Wedding.objects.create(
            title="David & Grâce", date=date(2027, 5, 24), venue="Salle Le Grand Royaume"
        )
    return created


def add_guest(client: APIClient, wedding: Wedding, **data: Any) -> dict[str, Any]:
    payload = {"name": "Famille Kouassi", "seats": 4, "category": "Famille", **data}
    response = client.post(reverse("wedding-guests", args=[wedding.pk]), payload, format="json")
    assert response.status_code == 201, response.json()
    created: dict[str, Any] = response.json()
    return created


def generate(client: APIClient, wedding: Wedding, guests: list[str]) -> dict[str, Any]:
    """Celery runs eagerly in tests: the batch is done when the call returns."""
    response = client.post(
        reverse("tickets-generate", args=[wedding.pk]), {"guests": guests}, format="json"
    )
    assert response.status_code == 202, response.json()
    data: dict[str, Any] = response.json()
    return data


def guest_row(client: APIClient, wedding: Wedding, guest_id: str) -> dict[str, Any]:
    rows = client.get(reverse("wedding-guests", args=[wedding.pk])).json()
    return next(row for row in rows if row["id"] == guest_id)


def token_of(url: str) -> str:
    return url.rsplit("/t/", 1)[1]


def decode(png: bytes) -> dict[str, str]:
    found = zxingcpp.read_barcodes(Image.open(io.BytesIO(png)))
    return {str(code.format): code.text for code in found}


# --- Tokens -----------------------------------------------------------------------------------


def test_tokens_are_signed_per_organization_and_cannot_be_forged() -> None:
    org_a, org_b = uuid.uuid4(), uuid.uuid4()
    token, token_id = tokens.new_token(org_a)
    parsed = tokens.parse(token)

    assert parsed is not None and parsed.ticket_id_hex == token_id
    assert tokens.verify(org_a, parsed)
    assert not tokens.verify(org_b, parsed)  # another agency's key
    forged = tokens.parse(token[:-2] + ("AA" if token[-2:] != "AA" else "BB"))
    assert forged is None or not tokens.verify(org_a, forged)
    assert tokens.parse("not-a-token") is None
    assert tokens.token_for(org_a, token_id) == token  # re-rendered QR: same token
    assert len(tokens.token_hash(token)) == 64


def test_the_ticket_key_comes_from_the_master_key(settings: Any) -> None:
    org = uuid.uuid4()
    settings.DOCUMENTS_MASTER_KEY = "first-master-key-0123456789abcdef"
    first = tokens.organization_key(org)
    settings.DOCUMENTS_MASTER_KEY = "second-master-key-0123456789abcdef"
    assert tokens.organization_key(org) != first
    assert tokens.organization_key(uuid.uuid4()) != tokens.organization_key(org)


def test_code_128_encodes_the_readable_code() -> None:
    values = barcodes.encode("WDV-DG-0001")
    assert values[0] == barcodes.START_B and values[-1] == barcodes.STOP
    assert sum(barcodes.modules("WDV-DG-0001")) == 11 * (len(values) - 1) + 13
    with pytest.raises(ValueError):
        barcodes.encode("é")


# --- Design and guests ------------------------------------------------------------------------


def test_the_design_starts_from_the_wedding(client: APIClient, wedding: Wedding) -> None:
    design = client.get(reverse("ticket-design", args=[wedding.pk])).json()

    assert design["partner_1"] == "David" and design["partner_2"] == "Grâce"
    assert design["venue"] == "Salle Le Grand Royaume"
    assert design["starts_at_local"] == "2027-05-24T15:00"  # the agency's zone
    updated = client.patch(
        reverse("ticket-design", args=[wedding.pk]),
        {"palette": "emeraude-or", "dress_code": "Blanc et or"},
        format="json",
    ).json()
    assert updated["palette"] == "emeraude-or"
    moved = client.patch(
        reverse("ticket-design", args=[wedding.pk]),
        {"starts_at_local": "2027-05-24T16:30"},
        format="json",
    ).json()
    assert moved["starts_at_local"] == "2027-05-24T16:30"
    bad = client.patch(
        reverse("ticket-design", args=[wedding.pk]), {"palette": "rouge"}, format="json"
    )
    assert bad.status_code == 400


def test_guests_are_imported_by_column_name(client: APIClient, wedding: Wedding) -> None:
    add_guest(client, wedding, name="Famille Kouassi")
    csv = (
        "Nom;Places;Catégorie;Table;Email\n"
        "Famille Kouassi;4;Famille;3;\n"
        "M. Yao;2;VIP;1;yao@mail.ci\n"
        ";;;;\n"
    )
    upload = SimpleUploadedFile("invites.csv", csv.encode(), content_type="text/csv")

    result = client.post(
        reverse("guest-import", args=[wedding.pk]), {"file": upload}, format="multipart"
    ).json()

    assert result["created"] == 1
    assert result["skipped"][0]["name"] == "Famille Kouassi"
    yao = next(
        g
        for g in client.get(reverse("wedding-guests", args=[wedding.pk])).json()
        if g["name"] == "M. Yao"
    )
    assert (yao["seats"], yao["category"], yao["table"]) == (2, "VIP", "1")


# --- Tickets ----------------------------------------------------------------------------------


def test_a_generated_ticket_carries_a_signed_qr_and_its_code(
    client: APIClient, wedding: Wedding, org_a: Organization
) -> None:
    guest = add_guest(client, wedding)
    batch = generate(client, wedding, [guest["id"]])
    row = guest_row(client, wedding, guest["id"])

    assert batch["total"] == 1
    progress = client.get(reverse("ticket-batch", args=[batch["batch"]])).json()
    assert (progress["status"], progress["done"]) == ("done", 1)
    assert row["ticket_state"] == "generated"
    assert row["ticket"]["code"] == "WDV-DG-0001"
    with tenant_context(org_a):
        ticket = Ticket.objects.get(pk=row["ticket"]["id"])
        png = services.image(ticket)
        assert ticket.document.pdf_file.name.startswith(f"org/{org_a.pk}/documents/")
    codes = decode(png)
    assert codes["QR Code"] == row["ticket"]["url"]
    assert codes["Code 128"] == "WDV-DG-0001"
    assert tokens.token_hash(token_of(row["ticket"]["url"])) == ticket.token_hash


def test_generating_again_reuses_the_document_until_something_changes(
    client: APIClient, wedding: Wedding, org_a: Organization
) -> None:
    guest = add_guest(client, wedding)
    generate(client, wedding, [guest["id"]])
    with tenant_context(org_a):
        first = Ticket.objects.get(guest_id=guest["id"]).document_id
    generate(client, wedding, [guest["id"]])
    with tenant_context(org_a):
        assert Ticket.objects.get(guest_id=guest["id"]).document_id == first
    client.patch(reverse("guest-detail", args=[guest["id"]]), {"seats": 5}, format="json")
    generate(client, wedding, [guest["id"]])
    with tenant_context(org_a):
        ticket = Ticket.objects.get(guest_id=guest["id"])
        assert ticket.document_id != first
        assert ticket.code == "WDV-DG-0001"  # same ticket, same QR


def test_the_guest_page_shows_the_ticket_and_takes_the_answer(
    client: APIClient, wedding: Wedding
) -> None:
    guest = add_guest(client, wedding)
    generate(client, wedding, [guest["id"]])
    token = token_of(guest_row(client, wedding, guest["id"])["ticket"]["url"])
    public = APIClient()

    page = public.get(reverse("public-ticket", args=[token]))
    assert page.status_code == 200
    assert page.json()["couple"] == "David & Grâce"
    assert page["X-Robots-Tag"] == "noindex, nofollow"
    assert public.get(reverse("public-ticket-image", args=[token]))["Content-Type"] == "image/png"
    assert public.get(reverse("public-ticket-pdf", args=[token])).content[:4] == b"%PDF"
    ics = public.get(reverse("public-ticket-ics", args=[token])).content.decode()
    assert "SUMMARY:Mariage de David & Grâce" in ics and "DTSTART:20270524T" in ics
    answer = public.post(
        reverse("public-ticket-rsvp", args=[token]), {"accepted": True}, format="json"
    )
    assert answer.json()["rsvp_status"] == "accepted"

    row = guest_row(client, wedding, guest["id"])
    assert row["ticket_state"] == "confirmed" and row["ticket"]["opened_at"] is not None


def test_a_forged_or_unknown_token_opens_nothing(client: APIClient, wedding: Wedding) -> None:
    guest = add_guest(client, wedding)
    generate(client, wedding, [guest["id"]])
    token = token_of(guest_row(client, wedding, guest["id"])["ticket"]["url"])
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    # Same bytes, other spelling: the last character's unused bits set (« …A » → « …B »).
    respelled = (
        token[:-1] + chr(ord(token[-1]) + 1) if token[-1] in "ACEGIKMOQSUWYacegikmoqsuwy" else None
    )

    for value in (tampered, "abc", tokens.new_token(uuid.uuid4())[0]):
        assert APIClient().get(reverse("public-ticket", args=[value])).status_code == 404
    if respelled:
        assert APIClient().get(reverse("public-ticket", args=[respelled])).status_code == 404


def test_cancel_then_reissue_gives_a_new_qr_and_kills_the_old_one(
    client: APIClient, wedding: Wedding
) -> None:
    guest = add_guest(client, wedding)
    generate(client, wedding, [guest["id"]])
    first = guest_row(client, wedding, guest["id"])["ticket"]
    old_token = token_of(first["url"])

    client.post(reverse("ticket-cancel", args=[first["id"]]))
    row = guest_row(client, wedding, guest["id"])
    assert row["ticket_state"] == "cancelled" and row["ticket"] is None
    assert (
        APIClient().get(reverse("public-ticket", args=[old_token])).json()["status"] == "cancelled"
    )
    refused = APIClient().post(
        reverse("public-ticket-rsvp", args=[old_token]), {"accepted": True}, format="json"
    )
    assert refused.status_code == 400

    fresh = client.post(reverse("ticket-reissue", args=[row["last_ticket_id"]])).json()
    assert fresh["code"] == "WDV-DG-0002" and fresh["url"] != first["url"]
    assert guest_row(client, wedding, guest["id"])["ticket_state"] == "generated"
    assert (
        APIClient().get(reverse("public-ticket", args=[old_token])).json()["status"] == "cancelled"
    )


def test_exports_hold_every_active_ticket(client: APIClient, wedding: Wedding) -> None:
    import pypdfium2 as pdfium

    ids = [add_guest(client, wedding, name=name)["id"] for name in ("Famille A", "Famille B")]
    generate(client, wedding, ids)

    pdf = client.get(reverse("tickets-export", args=[wedding.pk]), {"type": "pdf"}).content
    assert len(pdfium.PdfDocument(pdf)) == 2
    archive = zipfile.ZipFile(
        io.BytesIO(
            client.get(reverse("tickets-export", args=[wedding.pk]), {"type": "zip"}).content
        )
    )
    assert sorted(archive.namelist()) == [
        "WDV-DG-0001 - Famille A.pdf",
        "WDV-DG-0002 - Famille B.pdf",
    ]


def test_a_guest_whose_ticket_was_sent_is_not_deleted(
    client: APIClient, wedding: Wedding, org_a: Organization
) -> None:
    guest = add_guest(client, wedding)
    generate(client, wedding, [guest["id"]])
    with tenant_context(org_a):
        Ticket.objects.filter(guest_id=guest["id"]).update(sent_at="2027-04-01T10:00Z")

    assert client.delete(reverse("guest-detail", args=[guest["id"]])).status_code == 400


def test_the_design_preview_is_a_png(client: APIClient, wedding: Wedding) -> None:
    response = client.post(
        reverse("ticket-preview"),
        {"wedding": str(wedding.pk), "draft": {"palette": "bleu-royal", "partner_1": "Daniel"}},
        format="json",
    )
    assert response.status_code == 200 and response["Content-Type"] == "image/png"
    assert Image.open(io.BytesIO(response.content)).size[0] > 1000


# --- Roles and isolation ----------------------------------------------------------------------


def test_the_accountant_reads_but_does_not_issue(
    client_for: Callable[..., APIClient],
    make_member: Callable[..., User],
    org_a: Organization,
    wedding: Wedding,
) -> None:
    accountant = client_for(make_member(org_a, Membership.Role.ACCOUNTANT), org_a)
    assert accountant.get(reverse("wedding-guests", args=[wedding.pk])).status_code == 200
    denied = accountant.post(
        reverse("wedding-guests", args=[wedding.pk]), {"name": "X"}, format="json"
    )
    assert denied.status_code == 403


def test_another_agency_sees_nothing(
    client: APIClient,
    client_for: Callable[..., APIClient],
    owner_b: User,
    org_b: Organization,
    wedding: Wedding,
) -> None:
    guest = add_guest(client, wedding)
    generate(client, wedding, [guest["id"]])
    ticket_id = guest_row(client, wedding, guest["id"])["ticket"]["id"]
    other = client_for(owner_b, org_b)

    assert other.get(reverse("wedding-guests", args=[wedding.pk])).status_code == 404
    assert other.get(reverse("ticket-design", args=[wedding.pk])).status_code == 404
    assert (
        other.patch(
            reverse("guest-detail", args=[guest["id"]]), {"seats": 9}, format="json"
        ).status_code
        == 404
    )
    assert other.delete(reverse("guest-detail", args=[guest["id"]])).status_code == 404
    assert other.post(reverse("ticket-cancel", args=[ticket_id])).status_code == 404
    assert other.get(reverse("ticket-pdf", args=[ticket_id])).status_code == 404
    assert other.get(reverse("tickets-export", args=[wedding.pk])).status_code == 404


def test_guest_and_ticket_tables_are_under_row_level_security() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT relname FROM pg_class WHERE relrowsecurity AND relforcerowsecurity"
            " AND relname LIKE 'invitations_%'"
        )
        assert {row[0] for row in cursor.fetchall()} == {
            "invitations_guest",
            "invitations_ticket",
            "invitations_ticketdesign",
        }


def test_five_hundred_tickets_fit_the_three_minute_budget(
    wedding: Wedding, org_a: Organization
) -> None:
    """§6: 500 tickets in under 3 minutes. Measured on 10 (PDF only), extrapolated."""
    import time

    with tenant_context(org_a):
        guests = [Guest.objects.create(wedding=wedding, name=f"Invité {n}") for n in range(10)]
        started = time.perf_counter()
        for guest in guests:
            services.generate(services.issue_ticket(guest))
        per_ticket = (time.perf_counter() - started) / len(guests)
    assert per_ticket * 500 < 180, f"{per_ticket:.2f} s par billet"
