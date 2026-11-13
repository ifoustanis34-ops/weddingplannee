from __future__ import annotations

from types import SimpleNamespace

import pytest

from accounts.models import Membership
from core.permissions import IsOwner, read_any_write_roles, roles_allowed

ROLES = [role.value for role in Membership.Role]


def _request(role: str | None, method: str = "GET") -> SimpleNamespace:
    membership = SimpleNamespace(role=role) if role else None
    return SimpleNamespace(membership=membership, method=method)


@pytest.mark.parametrize("role", ROLES)
def test_only_owner_passes_is_owner(role: str) -> None:
    assert IsOwner().has_permission(_request(role), None) is (role == "owner")  # type: ignore[arg-type]


def test_roles_allowed_accepts_listed_roles_only() -> None:
    permission = roles_allowed("owner", "accountant")()

    assert permission.has_permission(_request("accountant"), None)  # type: ignore[arg-type]
    assert not permission.has_permission(_request("assistant"), None)  # type: ignore[arg-type]
    assert not permission.has_permission(_request(None), None)  # type: ignore[arg-type]


@pytest.mark.parametrize("role", ROLES)
def test_every_member_reads_but_only_writers_write(role: str) -> None:
    permission = read_any_write_roles(["owner", "planner"])()

    assert permission.has_permission(_request(role, "GET"), None)  # type: ignore[arg-type]
    can_write = permission.has_permission(_request(role, "PATCH"), None)  # type: ignore[arg-type]
    assert can_write is (role in {"owner", "planner"})
