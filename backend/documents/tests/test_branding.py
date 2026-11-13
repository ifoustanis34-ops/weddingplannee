"""Agency identity (docs/specs/devis-billets.md §4, §11)."""

from __future__ import annotations

import io
from collections.abc import Callable

import pytest
from django.core import signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import Membership, User
from core.signed_files import SALT
from core.tenant import tenant_context
from documents import images
from documents.models import OrganizationBranding
from organizations.models import Organization

URL = "/api/v1/organization/branding"
FILES = "/api/v1/organization/branding/files"


def png(
    color: tuple[int, int, int], size: tuple[int, int] = (200, 120), *, mark: bool = True
) -> bytes:
    """A logo: a coloured rectangle on a white background (with margins to trim)."""
    image = Image.new("RGB", size, (255, 255, 255))
    if mark:
        for x in range(50, 150):
            for y in range(30, 90):
                image.putpixel((x, y), color)
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


@pytest.fixture
def client(client_for: Callable[..., APIClient], owner_a: User, org_a: Organization) -> APIClient:
    return client_for(owner_a, org_a)


# --- Image processing ---------------------------------------------------------------------------


def test_the_real_type_is_checked_not_the_extension() -> None:
    with pytest.raises(Exception, match="PNG, JPG, WEBP ou SVG"):
        images.sniff(b"MZ\x90\x00 not an image at all")
    assert images.sniff(png((81, 38, 194))) == "PNG"


def test_a_plain_background_becomes_transparent_and_is_trimmed() -> None:
    processed = images.process_upload(png((81, 38, 194)))
    result = Image.open(io.BytesIO(processed.content))

    assert result.mode == "RGBA"
    assert result.getchannel("A").getpixel((0, 0)) == 0  # corner is now transparent
    assert result.width < 120  # 100 px mark + small margin, white margins gone
    assert processed.colors == ["#5126C2"]
    assert processed.contrast_light and processed.contrast_light > 4.5
    assert processed.contrast_dark and processed.contrast_dark < 3  # violet on dark ink


def test_svg_is_cleaned_of_scripts_handlers_and_external_links() -> None:
    dirty = b"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
      onload="alert(1)"><script>alert(2)</script>
      <rect width="10" height="10" fill="#C9A24A" onclick="steal()"/>
      <image xlink:href="https://evil.example/track.png"/>
      <a href="javascript:alert(3)"><circle r="2" fill="#0F1B3D"/></a>
      <foreignObject><div>x</div></foreignObject></svg>"""
    clean = images.sanitize_svg(dirty).decode()

    for forbidden in (
        "script",
        "onload",
        "onclick",
        "evil.example",
        "javascript:",
        "foreignObject",
    ):
        assert forbidden not in clean
    assert "#C9A24A" in clean and "<circle" in clean
    assert images.svg_colors(clean.encode()) == ["#C9A24A", "#0F1B3D"]


def test_svg_with_entities_is_refused() -> None:
    bomb = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><svg xmlns="http://www.w3.org/2000/svg">&a;</svg>'
    with pytest.raises(Exception, match="interdites"):
        images.sanitize_svg(bomb)


def test_files_over_five_megabytes_are_refused() -> None:
    with pytest.raises(Exception, match="5 Mo"):
        images.sniff(b"\x89PNG" + b"0" * (5 * 1024 * 1024 + 1))


def test_contrast_ratio_matches_wcag() -> None:
    assert images.contrast_ratio((0, 0, 0), (255, 255, 255)) == 21.0
    assert images.contrast_ratio((255, 255, 255), (255, 255, 255)) == 1.0


# --- API ----------------------------------------------------------------------------------------


def test_identity_is_created_from_the_settings_with_default_texts(
    client: APIClient, org_a: Organization
) -> None:
    data = client.get(URL).json()

    assert data["trade_name"] == "Agence A"
    assert data["monogram"] == "AA"
    assert len(data["activities"]) == 4 and len(data["engagements"]) == 4
    assert data["scripts"]["thanks"] == "Merci pour votre confiance !"
    assert set(data["missing"]) >= {"logo", "phones", "email"}
    assert data["files"]["logo"] is None


def test_owner_edits_texts_and_colours_within_limits(client: APIClient) -> None:
    ok = client.patch(
        URL,
        {
            "slogan": "Vos rêves, notre organisation",
            "primary_color": "#0f1b3d",
            "phones": ["+237 6 12 34 56 78"],
            "socials": {"instagram": "@mplanner", "myspace": "@x"},
            "activities": [
                {"label": "Mariages", "icon": "rings"},
                {"label": "Baptêmes", "icon": "??"},
            ],
        },
        format="json",
    )
    assert ok.status_code == 200, ok.json()
    body = ok.json()
    assert body["primary_color"] == "#0F1B3D"
    assert body["socials"] == {"instagram": "@mplanner"}
    assert body["activities"][1] == {"label": "Baptêmes", "icon": "star"}

    assert client.patch(URL, {"primary_color": "violet"}, format="json").status_code == 400
    five = [{"label": f"A{i}", "icon": "star"} for i in range(5)]
    assert client.patch(URL, {"activities": five}, format="json").status_code == 400


def test_logo_upload_is_processed_stored_per_organization_and_served_signed(
    client: APIClient, org_a: Organization
) -> None:
    upload = SimpleUploadedFile("logo.jpg", png((15, 27, 61)), content_type="image/jpeg")
    data = client.post(FILES, {"kind": "logo", "file": upload}, format="multipart").json()

    assert data["primary_color"] == "#0F1B3D"  # proposed from the logo
    assert "logo" not in data["missing"]
    with tenant_context(org_a):
        name = OrganizationBranding.objects.get().logo.name
    assert name.startswith(f"org/{org_a.pk}/branding/") and name.endswith(".png")

    served = APIClient().get(data["files"]["logo"])
    assert served.status_code == 200
    assert served["Content-Type"] == "image/png"

    removed = client.delete(f"{FILES}?kind=logo").json()
    assert removed["files"]["logo"] is None


def test_a_white_logo_is_flagged_as_unreadable_on_the_paper(client: APIClient) -> None:
    # A white mark on a dark background: the background is removed, the white drawing stays.
    image = Image.new("RGB", (200, 120), (20, 20, 20))
    for x in range(50, 150):
        for y in range(30, 90):
            image.putpixel((x, y), (250, 250, 250))
    out = io.BytesIO()
    image.save(out, format="PNG")
    upload = SimpleUploadedFile("logo.png", out.getvalue(), content_type="image/png")

    data = client.post(FILES, {"kind": "logo", "file": upload}, format="multipart").json()

    assert "logo_light" in data["warnings"]


def test_a_fake_image_is_refused(client: APIClient) -> None:
    upload = SimpleUploadedFile("logo.png", b"<html>not an image</html>", content_type="image/png")
    response = client.post(FILES, {"kind": "logo", "file": upload}, format="multipart")
    assert response.status_code == 400


def test_only_the_owner_manages_the_identity(
    client_for: Callable[..., APIClient], org_a: Organization, make_member: Callable[..., User]
) -> None:
    planner = client_for(make_member(org_a, Membership.Role.PLANNER), org_a)
    assert planner.get(URL).status_code == 403
    assert planner.patch(URL, {"slogan": "x"}, format="json").status_code == 403


def test_identities_are_isolated(
    client: APIClient,
    client_for: Callable[..., APIClient],
    org_b: Organization,
    owner_b: User,
) -> None:
    client.patch(URL, {"slogan": "Secret de A"}, format="json")
    data_b = client_for(owner_b, org_b).get(URL).json()

    assert data_b["trade_name"] == "Agence B"
    assert data_b["slogan"] == ""


def test_signed_urls_cannot_be_forged_or_redirected(client: APIClient, org_a: Organization) -> None:
    upload = SimpleUploadedFile("logo.png", png((81, 38, 194)), content_type="image/png")
    url = client.post(FILES, {"kind": "logo", "file": upload}, format="multipart").json()["files"][
        "logo"
    ]

    assert APIClient().get(url[:-3] + "abc").status_code == 404
    forged = signing.dumps("../config/settings/base.py", salt=SALT, compress=True)
    assert APIClient().get(reverse("signed-file", args=[forged])).status_code == 404
    other_salt = signing.dumps(url, salt="other", compress=True)
    assert APIClient().get(reverse("signed-file", args=[other_salt])).status_code == 404


def test_branding_is_under_row_level_security(db: None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT relrowsecurity AND relforcerowsecurity FROM pg_class"
            " WHERE relname = 'documents_organizationbranding'"
        )
        assert cursor.fetchone() == (True,)


def test_the_identity_logo_is_the_organization_logo(client: APIClient) -> None:
    assert client.get("/api/v1/organization").json()["logo"] is None
    assert client.get("/api/v1/dashboard/summary").json()["starter"]["has_logo"] is False

    upload = SimpleUploadedFile("logo.png", png((81, 38, 194)), content_type="image/png")
    client.post(FILES, {"kind": "logo", "file": upload}, format="multipart")

    assert client.get("/api/v1/organization").json()["logo"].startswith("/api/v1/files/")
