"""Current-organization context shared by the ORM, the database session and Celery tasks.

The active organization lives in a contextvar (safe across threads and asyncio tasks) and is
mirrored into the PostgreSQL setting ``app.current_org`` so Row-Level Security policies apply
even to raw SQL.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING

from django.db import connection, transaction

if TYPE_CHECKING:
    from organizations.models import Organization

_current_org: ContextVar[Organization | None] = ContextVar("current_org", default=None)


class TenantNotSetError(RuntimeError):
    """Raised when tenant-scoped data is queried without an active organization."""


def get_current_organization() -> Organization | None:
    return _current_org.get()


def require_current_organization() -> Organization:
    organization = _current_org.get()
    if organization is None:
        raise TenantNotSetError(
            "No active organization. Use tenant_context() or the all_tenants manager."
        )
    return organization


def _set_db_settings(current_org: str, bypass_rls: str) -> tuple[str, str]:
    """Set the RLS settings for the current transaction (``SET LOCAL``); return previous ones."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT coalesce(current_setting('app.current_org', true), ''),"
            " coalesce(current_setting('app.bypass_rls', true), 'off'),"
            " set_config('app.current_org', %s, true),"
            " set_config('app.bypass_rls', %s, true)",
            [current_org, bypass_rls],
        )
        previous_org, previous_bypass, _, _ = cursor.fetchone()
    return previous_org, previous_bypass


def set_db_tenant(organization_id: uuid.UUID | str | None, *, bypass: bool = False) -> None:
    _set_db_settings(str(organization_id) if organization_id else "", "on" if bypass else "off")


@contextmanager
def _db_tenant(organization_id: uuid.UUID | str | None, *, bypass: bool = False) -> Iterator[None]:
    """Scope the settings to this block, even when nested in an enclosing transaction."""
    with transaction.atomic():
        previous = _set_db_settings(
            str(organization_id) if organization_id else "", "on" if bypass else "off"
        )
        yield
        # On error the savepoint rollback already restores the settings (and the transaction
        # cannot run queries anymore), so restore explicitly only on a normal exit.
        _set_db_settings(*previous)


@contextmanager
def tenant_context(organization: Organization) -> Iterator[Organization]:
    """Activate an organization for the ORM and the database (requests, tasks, commands)."""
    token = _current_org.set(organization)
    try:
        with _db_tenant(organization.pk):
            yield organization
    finally:
        _current_org.reset(token)


@contextmanager
def tenant_context_for_id(organization_id: uuid.UUID | str) -> Iterator[Organization]:
    """Celery entry point: tasks receive an organization id and reactivate the context."""
    from organizations.models import Organization

    organization = Organization.objects.get(pk=organization_id, is_active=True)
    with tenant_context(organization) as active:
        yield active


@contextmanager
def bypass_tenant() -> Iterator[None]:
    """Lift RLS for cross-organization administration jobs. Use with the all_tenants manager."""
    token = _current_org.set(None)
    try:
        with _db_tenant(None, bypass=True):
            yield
    finally:
        _current_org.reset(token)
