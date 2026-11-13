"""Prospects → clients (reservations-stock.md §2): confirmed ones stay, the others are archived."""

from __future__ import annotations

import uuid

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from tests.factories import OrganizationFactory

pytestmark = pytest.mark.django_db(transaction=True)

BEFORE = [("crm", "0001_initial")]


def _latest() -> list[tuple[str, str]]:
    executor = MigrationExecutor(connection)
    nodes: list[tuple[str, str]] = executor.loader.graph.leaf_nodes()
    return nodes


def test_confirmed_prospects_become_clients_and_the_others_are_archived(
    django_db_serialized_rollback: None,
) -> None:
    executor = MigrationExecutor(connection)
    executor.migrate(BEFORE)
    old = executor.loader.project_state(BEFORE).apps
    Prospect = old.get_model("crm", "Prospect")
    # Only crm and its dependents were rolled back: the organization uses today's model.
    org = OrganizationFactory.create(slug=f"m-{uuid.uuid4().hex[:6]}")
    with connection.cursor() as cursor:
        cursor.execute("SET app.bypass_rls = 'on'")
    Prospect.objects.create(
        organization_id=org.pk, name="Nadia & Koffi", status="won", needs="500 invités"
    )
    Prospect.objects.create(organization_id=org.pk, name="Rokia & Moussa", status="lost")
    Prospect.objects.create(organization_id=org.pk, name="Fatou & Ibrahim", status="new")

    executor = MigrationExecutor(connection)
    executor.migrate(_latest())
    new = executor.loader.project_state(_latest()).apps
    Client = new.get_model("crm", "Client")
    clients = {c.name: c for c in Client.objects.filter(organization_id=org.pk)}
    with connection.cursor() as cursor:
        cursor.execute("RESET app.bypass_rls")

    assert set(clients) == {"Nadia & Koffi", "Rokia & Moussa", "Fatou & Ibrahim"}
    assert clients["Nadia & Koffi"].is_archived is False
    assert clients["Nadia & Koffi"].notes == "500 invités"
    assert clients["Rokia & Moussa"].is_archived is True
    assert clients["Fatou & Ibrahim"].is_archived is True
