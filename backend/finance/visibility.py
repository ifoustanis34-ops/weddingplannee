"""What each role may see of the money (CLAUDE.md §11)."""

from __future__ import annotations

from typing import Any

from accounts.models import Membership

Role = Membership.Role

# Owner and accountant: everything. Planner: balances only (no margins, no expenses).
# Assistant: nothing financial.
FULL = frozenset({Role.OWNER, Role.ACCOUNTANT})
BALANCES = frozenset({Role.OWNER, Role.ACCOUNTANT, Role.PLANNER})
MARGIN_KEYS = ("expenses", "margin", "margin_pct")


def can_see_balances(role: str | None) -> bool:
    return role in BALANCES


def can_see_margins(role: str | None) -> bool:
    return role in FULL


def strip_for_role(data: dict[str, Any], role: str | None) -> dict[str, Any] | None:
    if not can_see_balances(role):
        return None
    if can_see_margins(role):
        return data
    return {key: value for key, value in data.items() if key not in MARGIN_KEYS}
