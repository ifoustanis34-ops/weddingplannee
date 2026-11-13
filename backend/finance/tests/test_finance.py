from __future__ import annotations

import io
from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.urls import reverse
from openpyxl import load_workbook
from rest_framework.test import APIClient

from accounts.models import User
from contracts.models import Contract, Payment, PaymentSchedule
from core.models import AuditLog
from core.tenant import tenant_context
from crm.tests.factories import ClientFactory
from finance.models import Expense
from organizations.models import Organization
from quotes import services as quote_services

pytestmark = pytest.mark.django_db
NNBSP = " "


def make_contract(
    org: Organization,
    user: User,
    total: int = 1_500_000,
    *,
    name: str = "Awa & Moussa",
    expenses: int = 0,
    wedding_date: date | None = None,
) -> Contract:
    """Accepted quote → contract (deposit 30 %, balance 7 days before the wedding)."""
    with tenant_context(org):
        client = ClientFactory.create(name=name, email="client@mail.ci")
        quote = quote_services.create_quote(
            {
                "client": client,
                "wedding_date": wedding_date or date.today() + timedelta(days=120),
            },
            [
                quote_services.LineInput(
                    label="Mariage complet", unit="flat", unit_price=total, quantity=Decimal(1)
                )
            ],
            user=user,
        )
        quote_services.accept_quote(quote, user=user)
        contract = quote_services.convert_to_contract(quote, user=user)
        if expenses:
            Expense.objects.create(
                wedding=contract.wedding, label="Traiteur et salle", amount=expenses
            )
        return contract


@pytest.fixture
def client(client_for: Callable[..., APIClient], owner_a: User, org_a: Organization) -> APIClient:
    return client_for(owner_a, org_a)


def pay(client: APIClient, contract: Contract, amount: int, **extra: Any) -> Any:
    return client.post(
        reverse("contract-payments", args=[contract.pk]),
        {"amount": amount, "method": "orange_money", "reference": "OM-123", **extra},
        format="json",
    )


# --- Reference example (CLAUDE.md §7.5) -----------------------------------------------------


def test_reference_example(client: APIClient, org_a: Organization, owner_a: User) -> None:
    """CLAUDE.md §7.5: contract 1 500 000, expenses 900 000, margin 600 000,
    collected 500 000, balance 1 000 000."""
    contract = make_contract(org_a, owner_a, expenses=900_000)

    response = pay(client, contract, 500_000)

    assert response.status_code == 201, response.json()
    detail = response.json()
    assert (
        detail["total"],
        detail["expenses"],
        detail["margin"],
        detail["collected"],
        detail["balance"],
    ) == (
        1_500_000,
        900_000,
        600_000,
        500_000,
        1_000_000,
    )
    assert detail["margin_pct"] == 40.0
    assert detail["progress"] == 33
    # The 500 000 settles the 450 000 deposit, then 50 000 of the balance.
    assert [(s["label"], s["paid"], s["is_paid"]) for s in detail["schedule"]] == [
        ("Acompte", 450_000, True),
        ("Solde", 50_000, False),
    ]
    summary = client.get(reverse("finance-summary")).json()
    assert (summary["contracts_total"], summary["collected"], summary["balance_due"]) == (
        1_500_000,
        500_000,
        1_000_000,
    )
    assert (summary["expenses"], summary["margin"], summary["margin_pct"]) == (
        900_000,
        600_000,
        40.0,
    )
    dashboard = client.get(reverse("dashboard-summary")).json()
    assert dashboard["signature"]["to_collect"] == 1_000_000
    assert dashboard["performance"]["margin_avg"] == 40.0


def test_payment_cannot_exceed_the_balance(
    client: APIClient, org_a: Organization, owner_a: User
) -> None:
    contract = make_contract(org_a, owner_a)
    pay(client, contract, 500_000)

    response = pay(client, contract, 1_000_001)

    assert response.status_code == 400
    assert response.json() == {
        "code": "payment_exceeds_balance",
        "message": f"Le montant dépasse le solde restant (1{NNBSP}000{NNBSP}000 FCFA).",
        "fields": {"amount": [f"Maximum 1{NNBSP}000{NNBSP}000"]},
    }


def test_full_payment_completes_the_contract(
    client: APIClient, org_a: Organization, owner_a: User
) -> None:
    contract = make_contract(org_a, owner_a)

    pay(client, contract, 1_500_000)

    with tenant_context(org_a):
        contract.refresh_from_db()
        assert contract.status == Contract.Status.COMPLETED
        assert not PaymentSchedule.objects.filter(contract=contract, is_paid=False).exists()


def test_future_payment_date_is_refused(
    client: APIClient, org_a: Organization, owner_a: User
) -> None:
    contract = make_contract(org_a, owner_a)

    response = pay(client, contract, 1000, paid_at=(date.today() + timedelta(days=3)).isoformat())

    assert response.json()["fields"] == {"paid_at": ["Date future."]}


# --- Receipt, proof, cancellation -----------------------------------------------------------


def test_receipt_is_numbered_generated_and_emailed(
    client: APIClient, org_a: Organization, owner_a: User, django_capture_on_commit_callbacks: Any
) -> None:
    contract = make_contract(org_a, owner_a)
    mail.outbox.clear()

    with django_capture_on_commit_callbacks(execute=True):
        detail = pay(client, contract, 450_000).json()

    payment = detail["payments"][0]
    assert payment["receipt_number"] == f"RC-{date.today().year}-0001"
    assert mail.outbox[0].to == ["client@mail.ci"]
    name, content, mimetype = mail.outbox[0].attachments[0]
    assert (name, mimetype) == (f"RC-{date.today().year}-0001.pdf", "application/pdf")
    assert content[:4] == b"%PDF"
    receipt = client.get(reverse("payment-receipt", args=[payment["id"]]))
    assert receipt["Content-Type"] == "application/pdf"


def test_proof_upload(client: APIClient, org_a: Organization, owner_a: User) -> None:
    contract = make_contract(org_a, owner_a)
    proof = SimpleUploadedFile("capture-wave.png", b"\x89PNG fake", content_type="image/png")

    detail = client.post(
        reverse("contract-payments", args=[contract.pk]),
        {"amount": 100_000, "method": "wave", "proof": proof},
        format="multipart",
    ).json()

    payment = detail["payments"][0]
    assert payment["has_proof"] is True
    assert client.get(reverse("payment-proof", args=[payment["id"]])).content == b"\x89PNG fake"


def test_cancelled_payment_is_kept_traced_and_reallocated(
    client: APIClient, org_a: Organization, owner_a: User
) -> None:
    contract = make_contract(org_a, owner_a)
    payment_id = pay(client, contract, 500_000).json()["payments"][0]["id"]
    url = reverse("payment-cancel", args=[payment_id])

    assert client.post(url, {"reason": ""}, format="json").json()["fields"] == {
        "reason": ["Motif obligatoire."]
    }
    cancelled = client.post(url, {"reason": "Saisi deux fois"}, format="json").json()

    assert cancelled["is_cancelled"] is True
    detail = client.get(reverse("contract-detail", args=[contract.pk])).json()
    assert (detail["collected"], detail["balance"]) == (0, 1_500_000)
    assert all(not s["is_paid"] for s in detail["schedule"])
    with tenant_context(org_a):
        assert Payment.objects.filter(pk=payment_id).exists()  # never deleted
        assert AuditLog.objects.filter(action="payment.cancelled").exists()
    assert client.post(url, {"reason": "x"}, format="json").json()["code"] == "payment_cancelled"


# --- Schedule ---------------------------------------------------------------------------------


def test_schedule_can_be_split_but_must_match_the_total(
    client: APIClient, org_a: Organization, owner_a: User
) -> None:
    contract = make_contract(org_a, owner_a)
    url = reverse("contract-schedule", args=[contract.pk])
    today = date.today()

    wrong = client.put(
        url,
        {"installments": [{"label": "Acompte", "amount": 500_000, "due_date": today.isoformat()}]},
        format="json",
    )
    assert wrong.json()["code"] == "schedule_total_mismatch"

    response = client.put(
        url,
        {
            "installments": [
                {"label": "Acompte", "amount": 500_000, "due_date": today.isoformat()},
                {
                    "label": "Versement",
                    "amount": 500_000,
                    "due_date": (today + timedelta(days=40)).isoformat(),
                },
                {
                    "label": "Solde",
                    "amount": 500_000,
                    "due_date": (today + timedelta(days=100)).isoformat(),
                },
            ]
        },
        format="json",
    )
    assert response.status_code == 200, response.json()
    assert [s["label"] for s in response.json()["schedule"]] == ["Acompte", "Versement", "Solde"]


# --- Expenses, export -----------------------------------------------------------------------


def test_expenses_drive_the_margin(client: APIClient, org_a: Organization, owner_a: User) -> None:
    contract = make_contract(org_a, owner_a)
    wedding = client.get(reverse("contract-detail", args=[contract.pk])).json()["wedding"]

    created = client.post(
        reverse("expense-list"),
        {"wedding": wedding, "label": "DJ", "amount": 350_000},
        format="json",
    )
    assert created.status_code == 201
    client.post(
        reverse("expense-list"),
        {"wedding": wedding, "label": "Salle", "amount": 550_000},
        format="json",
    )

    detail = client.get(reverse("contract-detail", args=[contract.pk])).json()
    assert (detail["expenses"], detail["margin"]) == (900_000, 600_000)
    assert [e["label"] for e in detail["expense_items"]] == ["DJ", "Salle"]


def test_csv_and_excel_exports(client: APIClient, org_a: Organization, owner_a: User) -> None:
    make_contract(org_a, owner_a, expenses=900_000)

    csv_response = client.get(reverse("finance-export"), {"type": "csv"})
    text = csv_response.content.decode("utf-8-sig")
    assert text.splitlines()[0].startswith("Numéro;Client;Date du mariage")
    assert ";1500000;0;1500000;900000;600000" in text

    xlsx = client.get(reverse("finance-export"), {"type": "xlsx"})
    sheet = load_workbook(io.BytesIO(xlsx.content)).active
    assert sheet is not None
    assert sheet["B2"].value == "Awa & Moussa"
    assert sheet["I2"].value == 600_000
    with tenant_context(org_a):
        assert AuditLog.objects.filter(action="finance.exported").count() == 2


# --- Roles (CLAUDE.md §11) --------------------------------------------------------------------


def test_planner_reads_balances_but_not_margins(
    client_for: Callable[..., APIClient],
    org_a: Organization,
    owner_a: User,
    make_member: Callable[..., User],
) -> None:
    contract = make_contract(org_a, owner_a, expenses=900_000)
    planner = client_for(make_member(org_a, "planner"), org_a)

    detail = planner.get(reverse("contract-detail", args=[contract.pk])).json()
    assert detail["balance"] == 1_500_000
    assert "margin" not in detail and "expenses" not in detail and "expense_items" not in detail
    assert "margin" not in planner.get(reverse("finance-summary")).json()
    assert planner.get(reverse("dashboard-summary")).json()["performance"]["margin_avg"] is None
    assert pay(planner, contract, 1000).status_code == 403
    assert planner.get(reverse("finance-export")).status_code == 403
    assert planner.get(reverse("expense-list")).status_code == 403


def test_assistant_has_no_financial_access(
    client_for: Callable[..., APIClient],
    org_a: Organization,
    owner_a: User,
    make_member: Callable[..., User],
) -> None:
    contract = make_contract(org_a, owner_a)
    assistant = client_for(make_member(org_a, "assistant"), org_a)

    assert assistant.get(reverse("contract-list")).status_code == 403
    assert assistant.get(reverse("contract-detail", args=[contract.pk])).status_code == 403
    assert assistant.get(reverse("finance-summary")).status_code == 403
    dashboard = assistant.get(reverse("dashboard-summary")).json()
    assert dashboard["signature"] is None and dashboard["monthly"] is None
    assert "contract_total" not in dashboard["upcoming_weddings"][0]


def test_accountant_records_payments(
    client_for: Callable[..., APIClient],
    org_a: Organization,
    owner_a: User,
    make_member: Callable[..., User],
) -> None:
    contract = make_contract(org_a, owner_a)
    accountant = client_for(make_member(org_a, "accountant"), org_a)

    assert pay(accountant, contract, 450_000).status_code == 201
    assert accountant.get(reverse("finance-export")).status_code == 200


# --- Isolation --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "name", "target"),
    [
        ("get", "contract-detail", "contract"),
        ("post", "contract-payments", "contract"),
        ("put", "contract-schedule", "contract"),
        ("post", "payment-cancel", "payment"),
        ("get", "payment-receipt", "payment"),
        ("get", "payment-proof", "payment"),
    ],
)
def test_organization_b_cannot_reach_money_of_a(
    method: str,
    name: str,
    target: str,
    client: APIClient,
    client_for: Callable[..., APIClient],
    org_a: Organization,
    owner_a: User,
    org_b: Organization,
    owner_b: User,
) -> None:
    contract = make_contract(org_a, owner_a)
    payment_id = pay(client, contract, 1000).json()["payments"][0]["id"]
    target_id = contract.pk if target == "contract" else payment_id
    client_b = client_for(owner_b, org_b)

    response = getattr(client_b, method)(
        reverse(name, args=[target_id]),
        {"amount": 1, "method": "cash", "reason": "x", "installments": []},
        format="json",
    )

    assert response.status_code == 404
    assert client_b.get(reverse("contract-list")).json() == []
    assert client_b.get(reverse("finance-summary")).json()["collected"] == 0


def test_money_tables_are_under_row_level_security() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM pg_class"
            " WHERE relname IN ('contracts_payment', 'finance_expense')"
            " AND relrowsecurity AND relforcerowsecurity"
        )
        assert cursor.fetchone() == (2,)


def test_summary_lists_the_next_unpaid_installments(
    client: APIClient, org_a: Organization, owner_a: User
) -> None:
    """Complement §12 « Échéances à venir »: unpaid installments by due date, paid ones gone."""
    contract = make_contract(org_a, owner_a, wedding_date=date.today() + timedelta(days=60))
    upcoming = client.get(reverse("finance-summary")).json()["upcoming"]

    assert [row["remaining"] for row in upcoming] == [450_000, 1_050_000]
    assert upcoming[0]["client_name"] == "Awa & Moussa"
    assert upcoming[0]["is_overdue"] is False

    pay(client, contract, 450_000)
    remaining = client.get(reverse("finance-summary")).json()["upcoming"]
    assert [row["remaining"] for row in remaining] == [1_050_000]
