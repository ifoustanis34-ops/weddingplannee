"""Client records (docs/specs/reservations-stock.md §4.4). No pipeline, no follow-up."""

from __future__ import annotations

from typing import Any

from django.db import transaction

from accounts.models import User
from core import audit

from .models import Client

EDITABLE_FIELDS = (
    "name",
    "company",
    "phone",
    "phone_alt",
    "email",
    "address",
    "notes",
    "preferences",
    "is_archived",
)


@transaction.atomic
def create_client(data: dict[str, Any], *, user: User) -> Client:
    client = Client(created_by=user)
    for field in EDITABLE_FIELDS:
        if field in data:
            setattr(client, field, data[field])
    client.save()
    return client


@transaction.atomic
def update_client(client: Client, data: dict[str, Any]) -> Client:
    for field in EDITABLE_FIELDS:
        if field in data:
            setattr(client, field, data[field])
    client.save()
    return client


def ensure_active(client: Client) -> None:
    """A client who signs again leaves the archive (archived ≠ forgotten)."""
    if client.is_archived:
        client.is_archived = False
        client.save(update_fields=["is_archived", "updated_at"])


@transaction.atomic
def delete_client(client: Client, *, request: Any) -> None:
    """Soft delete (CLAUDE.md §11), traced in the audit log."""
    client.is_deleted = True
    client.save(update_fields=["is_deleted", "updated_at"])
    audit.record("client.deleted", client, request=request, changes={"name": client.name})
