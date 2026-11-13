"""Quote documents: one rendering, versioned generation, preview (devis-billets.md §3, §5)."""

from __future__ import annotations

import io
from collections.abc import Callable
from typing import Any
from unittest import mock

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.template.loader import render_to_string
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import User
from core.tenant import tenant_context
from crm.models import Client
from crm.tests.factories import ClientFactory
from documents import generation, icons, quote_document, rendering, samples
from documents.models import GeneratedDocument
from organizations.models import Organization
from quotes.models import Quote

pytestmark = pytest.mark.django_db

PREVIEW = reverse("document-preview")
LINES = [
    {"label": "Location de chaises", "unit": "unit", "unit_price": 1_000, "quantity": 250},
    {"label": "Décoration de la salle", "unit": "flat", "unit_price": 300_000, "quantity": 1},
    {"label": "Coordination du jour J", "unit": "flat", "unit_price": 150_000, "quantity": 1},
]


@pytest.fixture
def client(client_for: Callable[..., APIClient], owner_a: User, org_a: Organization) -> APIClient:
    return client_for(owner_a, org_a)


@pytest.fixture
def customer(org_a: Organization) -> Client:
    with tenant_context(org_a):
        created: Client = ClientFactory.create(name="M. & Mme Diallo", email="diallo@mail.com")
    return created


def create_quote(client: APIClient, customer: Client, **extra: Any) -> dict[str, Any]:
    payload = {
        "client": str(customer.pk),
        "wedding_date": "2027-02-14",
        "lines": LINES,
        "discount_pct": "4",
        **extra,
    }
    response = client.post(reverse("quote-list"), payload, format="json")
    assert response.status_code == 201, response.json()
    data: dict[str, Any] = response.json()
    return data


def page_size(png: bytes) -> tuple[int, int]:
    size: tuple[int, int] = Image.open(io.BytesIO(png)).size
    return size


# --- Engine ---------------------------------------------------------------------------------------


def test_the_fetcher_only_reads_the_template_and_the_organization_files(
    org_a: Organization, org_b: Organization
) -> None:
    from weasyprint.urls import URLFetcher

    fetcher: URLFetcher = rendering._fetcher(str(org_a.pk))
    own = default_storage.save(f"org/{org_a.pk}/branding/a.png", ContentFile(b"\x89PNG"))
    other = default_storage.save(f"org/{org_b.pk}/branding/b.png", ContentFile(b"\x89PNG"))

    assert fetcher.fetch(rendering.file_url(own)).status == 200
    assert (
        fetcher.fetch(rendering.asset_url("fonts/great-vibes-latin-400-normal.woff")).status == 200
    )
    for blocked in (
        rendering.file_url(other),
        rendering.asset_url("../config/settings/base.py"),
        "https://example.com/tracker.png",
        "file:///etc/passwd",
    ):
        with pytest.raises(rendering.BlockedResource):
            fetcher.fetch(blocked)


@pytest.mark.parametrize("design", ["A", "B", "C", "D"])
def test_each_design_fits_the_sample_quote_on_one_a4_page(design: str) -> None:
    snapshot = samples.quote_snapshot(design)
    result = generation.render(snapshot)

    assert result.pdf[:4] == b"%PDF"
    assert result.page_count == 1
    width, height = page_size(result.pages[0])
    assert abs(height / width - 297 / 210) < 0.01  # A4 portrait


def test_forty_lines_run_over_several_pages_with_page_numbers() -> None:
    snapshot = samples.quote_snapshot("A")
    lines = snapshot["quote"]["lines"]
    snapshot["quote"]["lines"] = [lines[i % len(lines)] for i in range(40)]

    result = generation.render(snapshot)

    assert result.page_count >= 3
    html = render_to_string(
        quote_document.template_path(snapshot),
        {**quote_document.context(snapshot), "multipage": True},
    )
    assert 'class="pageno"' in html and "suite" in html


def test_long_texts_shrink_then_are_cut_never_overflow() -> None:
    assert quote_document.fit("Court", base=10, minimum=7, room=20) == {"text": "Court", "size": 10}
    shrunk = quote_document.fit("x" * 25, base=10, minimum=7, room=20)
    assert shrunk["size"] == 8 and shrunk["text"] == "x" * 25
    cut = quote_document.fit("y" * 100, base=10, minimum=7, room=20)
    assert cut["size"] == 7 and cut["text"].endswith("…") and len(cut["text"]) <= 28


def test_watermark_on_drafts_and_accepted_quotes_only() -> None:
    for status, mark in (("draft", "BROUILLON"), ("accepted", "ACCEPTÉ"), ("sent", "")):
        snapshot = {**samples.quote_snapshot("C"), "status": status}
        assert quote_document.context(snapshot)["watermark"] == mark


def test_partners_are_named_and_sign_on_every_design() -> None:
    for design in ("A", "D"):
        snapshot = samples.quote_snapshot(design)
        snapshot["partners"] = [
            {
                "name": "SAGUIE ETEMO",
                "activity": "Wedding Planner & Event Design",
                "signatory": "",
                "signatory_role": "La Responsable",
                "logo": None,
                "signature": None,
            }
        ]
        html = render_to_string(
            quote_document.template_path(snapshot), quote_document.context(snapshot)
        )
        assert "SAGUIE ETEMO" in html and "En partenariat avec" in html


def test_service_icons_are_guessed_from_the_name() -> None:
    assert icons.guess("Location de chaises") == "chair"
    assert icons.guess("Menu traiteur ivoirien") == "plate"
    assert icons.guess("Pièce montée") == "cake"
    assert icons.guess("Quelque chose") == icons.FALLBACK


# --- API ------------------------------------------------------------------------------------------


def test_preview_of_unsaved_editor_data_is_a_cached_png(
    client: APIClient, customer: Client, org_a: Organization
) -> None:
    draft = {"client": str(customer.pk), "lines": LINES, "design": "B", "palette": "emeraude-or"}
    with mock.patch.object(generation, "render", wraps=generation.render) as render:
        first = client.post(PREVIEW, {"kind": "quote", "draft": draft}, format="json")
        second = client.post(PREVIEW, {"kind": "quote", "draft": draft}, format="json")

    assert first.status_code == 200 and first["Content-Type"] == "image/png"
    assert first["X-Page-Count"] == "1"
    assert first.content == second.content
    assert render.call_count == 1  # second answer from the cache
    with tenant_context(org_a):
        assert not Quote.objects.exists()  # nothing saved


def test_generation_is_versioned_and_never_silent(
    client: APIClient, customer: Client, org_a: Organization
) -> None:
    quote = create_quote(client, customer, design="C", tagline="Un jour inoubliable.")
    url = reverse("quote-generate", args=[quote["id"]])

    first = client.post(url).json()
    again = client.post(url).json()
    client.patch(reverse("quote-detail", args=[quote["id"]]), {"discount_pct": "10"}, format="json")
    changed = client.post(url).json()

    assert first["version"] == 1 and again["id"] == first["id"]
    assert changed["version"] == 2 and changed["sha256"] != first["sha256"]
    with tenant_context(org_a):
        document = GeneratedDocument.objects.get(pk=first["id"])
        assert document.pdf_file.name.startswith(f"org/{org_a.pk}/documents/")
        assert document.data_snapshot["quote"]["total"] == 672_000  # 700 000 − 4 %
        assert document.template.code == "C"
    assert APIClient().get(first["pdf_url"]).status_code == 200


def test_preview_png_and_generated_png_are_identical(
    client: APIClient, customer: Client, org_a: Organization
) -> None:
    """Parity (§12): the editor preview and the stored document come from one rendering."""
    quote = create_quote(client, customer)
    preview = client.post(PREVIEW, {"kind": "quote", "quote": quote["id"]}, format="json")
    generated = client.post(reverse("quote-generate", args=[quote["id"]])).json()

    with (
        tenant_context(org_a),
        GeneratedDocument.objects.get(pk=generated["id"]).png_file.open() as f,
    ):
        stored = f.read()
    assert preview.content == stored


def test_documents_of_another_agency_cannot_be_previewed_or_generated(
    client: APIClient, client_for: Callable[..., APIClient], owner_b: User, org_b: Organization
) -> None:
    with tenant_context(org_b):
        other = ClientFactory.create(name="Client B")
    quote_b = create_quote(client_for(owner_b, org_b), other)

    assert (
        client.post(PREVIEW, {"kind": "quote", "quote": quote_b["id"]}, format="json").status_code
        == 404
    )
    assert client.post(reverse("quote-generate", args=[quote_b["id"]])).status_code == 404
    assert client.get(reverse("quote-pdf", args=[quote_b["id"]])).status_code == 404


def test_send_attaches_the_frozen_version(
    client: APIClient,
    customer: Client,
    org_a: Organization,
    django_capture_on_commit_callbacks: Any,
) -> None:
    from django.core import mail

    quote = create_quote(client, customer)
    with django_capture_on_commit_callbacks(execute=True):
        client.post(reverse("quote-send", args=[quote["id"]]))

    with tenant_context(org_a):
        document = GeneratedDocument.objects.get(object_id=quote["id"])
        stored = generation.pdf_bytes(document)
    assert mail.outbox[-1].attachments[0][1] == stored
    with tenant_context(org_a):
        token = Quote.objects.get(pk=quote["id"]).public_token
    public = APIClient().get(reverse("public-quote-pdf", args=[token]))
    assert public.content == stored


def test_designs_and_palettes_come_from_the_server(client: APIClient) -> None:
    data = client.get(reverse("document-designs")).json()

    assert [d["code"] for d in data["designs"]] == ["A", "B", "C", "D"]
    assert {"code": "nuit-or", "name": "Nuit & Or", "dark": "#0F1B3D", "accent": "#C9A24A"} in data[
        "palettes"
    ]
    assert data["default_design"] == "A"


def test_public_page_shows_the_sent_document_and_is_not_indexed(
    client: APIClient,
    customer: Client,
    org_a: Organization,
    django_capture_on_commit_callbacks: Any,
) -> None:
    quote = create_quote(client, customer, design="D", partners=[{"name": "SAGUIE ETEMO"}])
    with django_capture_on_commit_callbacks(execute=True):
        client.post(reverse("quote-send", args=[quote["id"]]))
    with tenant_context(org_a):
        token = Quote.objects.get(pk=quote["id"]).public_token
        assert Quote.objects.get(pk=quote["id"]).partners.get().name == "SAGUIE ETEMO"

    response = APIClient().get(reverse("public-quote-preview", args=[token]))

    assert response.status_code == 200 and response["Content-Type"] == "image/png"
    assert response["X-Robots-Tag"] == "noindex, nofollow"
    assert response["Referrer-Policy"] == "no-referrer"


@pytest.mark.parametrize("design", ["A", "B", "C", "D"])
def test_a_short_quote_with_the_default_texts_stays_on_one_page(design: str) -> None:
    """New agencies keep the default activities and engagements (longer than the sample's)."""
    from documents.models import default_activities, default_engagements

    snapshot = samples.quote_snapshot(design)
    snapshot["agency"]["activities"] = default_activities()
    snapshot["agency"]["engagements"] = default_engagements()
    snapshot["quote"].update(tagline="", lines=snapshot["quote"]["lines"][:3])
    snapshot["quote"]["event"]["venue"] = ""

    assert generation.render(snapshot).page_count == 1
