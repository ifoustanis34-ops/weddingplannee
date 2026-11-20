from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import pytest
from django.core import mail
from django.db import connection
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Membership, User
from catalog.defaults import create_sample_catalog
from catalog.models import ServiceItem
from contracts.models import Contract, PaymentSchedule
from core.tenant import tenant_context
from crm.models import Client
from crm.tests.factories import ClientFactory
from events.models import Wedding
from organizations.models import Organization
from organizations.numbering import next_number
from quotes.models import Quote
from quotes.tasks import expire_quotes

pytestmark = pytest.mark.django_db

LIST = reverse("quote-list")


@pytest.fixture
def client(client_for: Callable[..., APIClient], owner_a: User, org_a: Organization) -> APIClient:
    return client_for(owner_a, org_a)


@pytest.fixture
def customer(org_a: Organization) -> Client:
    with tenant_context(org_a):
        created: Client = ClientFactory.create(name="Awa & Moussa", email="awa@mail.ci")
    return created


@pytest.fixture
def catalog(org_a: Organization) -> dict[str, ServiceItem]:
    with tenant_context(org_a):
        create_sample_catalog()
        return {item.name: item for item in ServiceItem.objects.all()}


def three_lines(catalog: dict[str, ServiceItem]) -> list[dict[str, Any]]:
    menu = catalog["Menu traiteur ivoirien"]
    deco = catalog["Décoration de salle"]
    return [
        {
            "service_item": str(menu.pk),
            "label": menu.name,
            "unit": "guest",
            "unit_price": 12_000,
            "quantity": 250,
        },
        {
            "service_item": str(deco.pk),
            "label": deco.name,
            "unit": "flat",
            "unit_price": 900_000,
            "quantity": 1,
        },
        {
            "label": "Photographe (ligne libre)",
            "unit": "day",
            "unit_price": 300_000,
            "quantity": "1.5",
        },
    ]


def create(
    client: APIClient, customer: Client, lines: list[dict[str, Any]], **extra: Any
) -> dict[str, Any]:
    response = client.post(
        LIST,
        {
            "client": str(customer.pk),
            "wedding_date": "2026-12-19",
            "guest_count": 250,
            "lines": lines,
            "discount_pct": 10,
            "deposit_pct": 30,
            **extra,
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    body: dict[str, Any] = response.json()
    return body


# --- Creation and server-side totals ----------------------------------------------------------


def test_quote_with_three_catalog_services(
    client: APIClient, customer: Client, catalog: dict[str, ServiceItem]
) -> None:
    body = create(client, customer, three_lines(catalog))

    year = timezone.localdate().year
    assert body["number"] == f"DV-{year}-0001"
    assert body["status"] == "draft"
    assert [line["amount"] for line in body["lines"]] == [3_000_000, 900_000, 450_000]
    assert (body["subtotal"], body["discount_amount"], body["total"], body["deposit_amount"]) == (
        4_350_000,
        435_000,
        3_915_000,
        1_174_500,
    )
    # Validity defaults to 30 days.
    assert body["wedding_date"] == "2026-12-19"
    assert body["guest_count"] == 250
    assert body["valid_until"] == (timezone.localdate() + timedelta(days=30)).isoformat()


def test_client_totals_are_ignored(client: APIClient, customer: Client) -> None:
    body = create(
        client,
        customer,
        [{"label": "Coordination", "unit_price": 500_000, "quantity": 1, "amount": 1}],
        total=1,
    )

    assert body["total"] == 450_000  # 500 000 − 10 %


def test_update_replaces_lines_and_recomputes(client: APIClient, customer: Client) -> None:
    body = create(client, customer, [{"label": "A", "unit_price": 100_000, "quantity": 1}])
    url = reverse("quote-detail", args=[body["id"]])

    updated = client.patch(
        url,
        {"discount_pct": 0, "lines": [{"label": "B", "unit_price": 200_000, "quantity": 2}]},
        format="json",
    ).json()

    assert [line["label"] for line in updated["lines"]] == ["B"]
    assert updated["total"] == 400_000


@pytest.mark.django_db(transaction=True)
def test_numbers_are_unique_under_concurrency(org_a: Organization) -> None:
    """Parallel requests each get their own number (row lock on the sequence)."""
    numbers: list[str] = []
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            with tenant_context(org_a):
                numbers.append(next_number("quote"))
        except BaseException as exc:  # pragma: no cover - reported below
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert len(set(numbers)) == 8


# --- Sending ----------------------------------------------------------------------------------


def test_send_generates_pdf_and_emails_the_client(
    client: APIClient,
    customer: Client,
    catalog: dict[str, ServiceItem],
    django_capture_on_commit_callbacks: Any,
) -> None:
    body = create(client, customer, three_lines(catalog))

    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(reverse("quote-send", args=[body["id"]]))

    assert response.status_code == 200, response.json()
    assert response.json()["status"] == "sent"
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == ["awa@mail.ci"]
    assert body["public_url"] in message.body
    attachment_name, content, mimetype = message.attachments[0]
    assert (attachment_name, mimetype) == (f"{body['number']}.pdf", "application/pdf")
    assert content[:4] == b"%PDF"


def test_send_requires_a_verified_sender(
    client_for: Callable[..., APIClient],
    org_a: Organization,
    make_member: Callable[..., User],
    customer: Client,
) -> None:
    user = make_member(org_a, Membership.Role.PLANNER, is_verified=False)
    client = client_for(user, org_a)
    body = create(client, customer, [{"label": "A", "unit_price": 1, "quantity": 1}])

    response = client.post(reverse("quote-send", args=[body["id"]]))

    assert response.status_code == 403
    assert response.json()["code"] == "email_not_verified"


def test_send_requires_the_client_email(client: APIClient, org_a: Organization) -> None:
    with tenant_context(org_a):
        no_email = ClientFactory.create(email="")
    body = create(client, no_email, [{"label": "A", "unit_price": 1, "quantity": 1}])

    response = client.post(reverse("quote-send", args=[body["id"]]))

    assert response.json()["code"] == "client_email_missing"


def test_send_by_whatsapp_needs_no_email_and_sends_none(
    client_for: Callable[..., APIClient],
    org_a: Organization,
    make_member: Callable[..., User],
    django_capture_on_commit_callbacks: Any,
) -> None:
    user = make_member(org_a, Membership.Role.PLANNER, is_verified=False)
    client = client_for(user, org_a)
    with tenant_context(org_a):
        no_email = ClientFactory.create(email="")
    body = create(client, no_email, [{"label": "A", "unit_price": 1, "quantity": 1}])

    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(
            reverse("quote-send", args=[body["id"]]), {"channel": "whatsapp"}, format="json"
        )

    assert response.status_code == 200, response.json()
    assert response.json()["status"] == "sent"
    assert mail.outbox == []


def test_pdf_download(client: APIClient, customer: Client) -> None:
    body = create(
        client, customer, [{"label": "Coordination", "unit_price": 500_000, "quantity": 1}]
    )

    response = client.get(reverse("quote-pdf", args=[body["id"]]))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"


# --- Public page and decision -----------------------------------------------------------------


def sent_quote(client: APIClient, customer: Client, captured: Any) -> dict[str, Any]:
    body = create(
        client, customer, [{"label": "Coordination", "unit_price": 1_500_000, "quantity": 1}]
    )
    with captured(execute=True):
        client.post(reverse("quote-send", args=[body["id"]]))
    return body


def test_public_link_shows_quote_and_client_accepts(
    client: APIClient,
    customer: Client,
    org_a: Organization,
    django_capture_on_commit_callbacks: Any,
) -> None:
    body = sent_quote(client, customer, django_capture_on_commit_callbacks)
    token = body["public_url"].rsplit("/", 1)[1]
    visitor = APIClient()

    page = visitor.get(reverse("public-quote", args=[token]))
    assert page.status_code == 200
    assert page.json()["client_name"] == "Awa & Moussa"
    assert page.json()["organization"]["name"] == "Agence A"
    assert "id" not in page.json()

    accepted = visitor.post(reverse("public-quote-accept", args=[token]))
    assert accepted.json()["status"] == "accepted"
    again = visitor.post(reverse("public-quote-accept", args=[token]))
    assert again.status_code == 400

    pdf = visitor.get(reverse("public-quote-pdf", args=[token]))
    assert pdf.content[:4] == b"%PDF"


def test_drafts_and_unknown_tokens_are_not_public(client: APIClient, customer: Client) -> None:
    body = create(client, customer, [{"label": "A", "unit_price": 1, "quantity": 1}])
    token = body["public_url"].rsplit("/", 1)[1]

    assert APIClient().get(reverse("public-quote", args=[token])).status_code == 404
    assert APIClient().get(reverse("public-quote", args=["inconnu"])).status_code == 404


def test_expired_quote_cannot_be_accepted(
    client: APIClient,
    customer: Client,
    org_a: Organization,
    django_capture_on_commit_callbacks: Any,
) -> None:
    body = sent_quote(client, customer, django_capture_on_commit_callbacks)
    with tenant_context(org_a):
        Quote.objects.filter(pk=body["id"]).update(
            valid_until=timezone.localdate() - timedelta(days=1)
        )

    assert expire_quotes() == 1
    token = body["public_url"].rsplit("/", 1)[1]
    response = APIClient().post(reverse("public-quote-accept", args=[token]))
    assert response.status_code == 400
    assert response.json()["code"] == "quote_closed"


# --- Conversion -------------------------------------------------------------------------------


def test_convert_creates_contract_schedule_wedding_and_unarchives_client(
    client: APIClient, customer: Client, org_a: Organization
) -> None:
    with tenant_context(org_a):
        Client.objects.filter(pk=customer.pk).update(is_archived=True)
    body = create(
        client,
        customer,
        [{"label": "Prestation complète", "unit_price": 1_500_000, "quantity": 1}],
        discount_pct=0,
        deposit_pct=30,
    )
    client.post(reverse("quote-accept", args=[body["id"]]))

    response = client.post(reverse("quote-convert", args=[body["id"]]))

    assert response.status_code == 201, response.json()
    year = timezone.localdate().year
    assert response.json()["contract"]["number"] == f"CT-{year}-0001"
    with tenant_context(org_a):
        contract = Contract.objects.get()
        schedule = list(
            PaymentSchedule.objects.filter(contract=contract).values_list(
                "label", "amount", "due_date"
            )
        )
        wedding = Wedding.objects.get()
    assert contract.total == 1_500_000
    assert schedule == [
        ("Acompte", 450_000, timezone.localdate()),
        ("Solde", 1_050_000, date(2026, 12, 12)),
    ]
    assert (wedding.title, wedding.guest_count, wedding.contract_id) == (
        "Awa & Moussa",
        250,
        contract.pk,
    )
    with tenant_context(customer.organization):
        customer.refresh_from_db()
    assert customer.is_archived is False
    assert wedding.client_id == customer.pk
    assert client.post(reverse("quote-convert", args=[body["id"]])).status_code == 400


def test_only_accepted_quotes_convert(client: APIClient, customer: Client) -> None:
    body = create(client, customer, [{"label": "A", "unit_price": 1, "quantity": 1}])

    response = client.post(reverse("quote-convert", args=[body["id"]]))

    assert response.json()["code"] == "quote_not_accepted"


def test_accepted_quote_is_locked_but_can_be_duplicated(
    client: APIClient, customer: Client
) -> None:
    body = create(client, customer, [{"label": "A", "unit_price": 100, "quantity": 1}])
    client.post(reverse("quote-accept", args=[body["id"]]))

    locked = client.patch(reverse("quote-detail", args=[body["id"]]), {"notes": "x"}, format="json")
    assert locked.json()["code"] == "quote_locked"

    copy = client.post(reverse("quote-duplicate", args=[body["id"]]), {}, format="json").json()
    assert copy["status"] == "draft"
    assert copy["number"] != body["number"]
    assert copy["total"] == body["total"]


def test_templates_are_reusable_and_unnumbered(
    client: APIClient, customer: Client, org_a: Organization
) -> None:
    body = create(
        client, customer, [{"label": "Formule Or", "unit_price": 2_000_000, "quantity": 1}]
    )
    template = client.post(
        reverse("quote-duplicate", args=[body["id"]]), {"as_template": True}, format="json"
    ).json()
    assert (template["is_template"], template["number"], template["client"]) == (True, "", None)
    assert [q["id"] for q in client.get(LIST).json()["results"]] == [body["id"]]

    with tenant_context(org_a):
        other = ClientFactory.create(name="Fatou & Ibra")
    from_template = client.post(
        reverse("quote-duplicate", args=[template["id"]]),
        {"client": str(other.pk)},
        format="json",
    ).json()
    assert from_template["client"] == str(other.pk)
    assert from_template["lines"][0]["label"] == "Formule Or"


# --- Roles and isolation ----------------------------------------------------------------------


def test_accountant_reads_quotes_but_cannot_create(
    client_for: Callable[..., APIClient],
    org_a: Organization,
    make_member: Callable[..., User],
    customer: Client,
) -> None:
    client = client_for(make_member(org_a, "accountant"), org_a)

    assert client.get(LIST).status_code == 200
    response = client.post(LIST, {"client": str(customer.pk), "lines": []}, format="json")
    assert response.status_code == 403


def test_assistant_cannot_convert_into_contract(
    client: APIClient,
    client_for: Callable[..., APIClient],
    org_a: Organization,
    make_member: Callable[..., User],
    customer: Client,
) -> None:
    body = create(client, customer, [{"label": "A", "unit_price": 1, "quantity": 1}])
    client.post(reverse("quote-accept", args=[body["id"]]))
    assistant = client_for(make_member(org_a, "assistant"), org_a)

    assert assistant.post(reverse("quote-convert", args=[body["id"]])).status_code == 403


@pytest.mark.parametrize(
    ("method", "name"),
    [
        ("get", "quote-detail"),
        ("patch", "quote-detail"),
        ("delete", "quote-detail"),
        ("post", "quote-send"),
        ("post", "quote-accept"),
        ("post", "quote-refuse"),
        ("post", "quote-duplicate"),
        ("post", "quote-convert"),
        ("get", "quote-pdf"),
    ],
)
def test_organization_b_cannot_reach_quotes_of_a(
    method: str,
    name: str,
    client: APIClient,
    client_for: Callable[..., APIClient],
    customer: Client,
    org_b: Organization,
    owner_b: User,
) -> None:
    body = create(client, customer, [{"label": "A", "unit_price": 1, "quantity": 1}])

    response = getattr(client_for(owner_b, org_b), method)(
        reverse(name, args=[body["id"]]), {}, format="json"
    )

    assert response.status_code == 404


def test_quote_cannot_target_a_client_of_another_organization(
    client_for: Callable[..., APIClient], org_b: Organization, owner_b: User, customer: Client
) -> None:
    response = client_for(owner_b, org_b).post(
        LIST, {"client": str(customer.pk), "lines": []}, format="json"
    )

    assert response.status_code == 400
    assert "client" in response.json()["fields"]


def test_quote_tables_are_under_row_level_security() -> None:
    tables = [
        "catalog_servicecategory",
        "catalog_serviceitem",
        "quotes_quote",
        "quotes_quoteline",
        "contracts_contract",
        "contracts_paymentschedule",
        "events_wedding",
        "organizations_documentsequence",
    ]
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT relname FROM pg_class WHERE relname = ANY(%s)"
            " AND relrowsecurity AND relforcerowsecurity",
            [tables],
        )
        assert sorted(row[0] for row in cursor.fetchall()) == sorted(tables)


def test_list_tiles_follow_the_complement_rules(client: APIClient, org_a: Organization) -> None:
    """Complement §16: median creation time over 30 days, acceptance over 90 days."""
    now = timezone.now()
    with tenant_context(org_a):
        customer = ClientFactory.create(name="Patricia Ouattara")
        rows = [
            # (created minutes ago, sent minutes ago, status, total)
            (40, 20, Quote.Status.SENT, 4_350_000),
            (90, 60, Quote.Status.SENT, 2_140_000),
            (300, 200, Quote.Status.ACCEPTED, 3_600_000),
        ]
        for created, sent, status, total in rows:
            quote = Quote.objects.create(
                client=customer,
                issue_date=date.today(),
                valid_until=date.today() + timedelta(days=30),
                status=status,
                total=total,
                sent_at=now - timedelta(minutes=sent),
                accepted_at=now if status == Quote.Status.ACCEPTED else None,
            )
            Quote.objects.filter(pk=quote.pk).update(created_at=now - timedelta(minutes=created))
        Quote.objects.create(
            client=customer,
            issue_date=date.today(),
            valid_until=date.today(),
            status=Quote.Status.REFUSED,
            refused_at=now,
        )

    stats = client.get("/api/v1/quotes/stats").json()

    assert stats["median_creation_minutes"] == 30  # 20, 30 and 100 minutes
    assert stats["sent_this_month"] >= 2
    assert stats["acceptance_rate"] == 50  # 1 accepted, 1 refused
    assert stats["pending_amount"] == 6_490_000


def test_quote_stats_stay_in_the_organization(
    client_for: Callable[..., APIClient], org_a: Organization, org_b: Organization, owner_b: User
) -> None:
    with tenant_context(org_a):
        Quote.objects.create(
            client=ClientFactory.create(),
            issue_date=date.today(),
            valid_until=date.today(),
            status=Quote.Status.SENT,
            total=1_000_000,
        )
    stats = client_for(owner_b, org_b).get("/api/v1/quotes/stats").json()
    assert stats["pending_amount"] == 0


def test_sending_plans_no_reminder_and_lists_flag_converted_quotes(
    client: APIClient, customer: Client, django_capture_on_commit_callbacks: Any
) -> None:
    """Reminders are gone (reservations-stock.md §2): sending emails the quote once, nothing else.

    The list tells which quotes became contracts."""
    quote = sent_quote(client, customer, django_capture_on_commit_callbacks)
    detail = client.get(reverse("quote-detail", args=[quote["id"]])).json()
    assert "next_reminder_at" not in detail

    client.post(reverse("quote-accept", args=[quote["id"]]))
    client.post(reverse("quote-convert", args=[quote["id"]]))
    rows = client.get(reverse("quote-list")).json()["results"]
    assert [row["has_contract"] for row in rows] == [True]
