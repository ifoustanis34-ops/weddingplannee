from rest_framework.permissions import BasePermission

from accounts.models import Membership
from core.permissions import IsTenantMember, WeddingsEnabled, read_any_write_roles

Role = Membership.Role

# Weddings, tasks and vendors (CLAUDE.md §11): owner, planner and assistant act, accountant reads.
PERMISSIONS: list[type[BasePermission]] = [
    IsTenantMember,
    read_any_write_roles([Role.OWNER, Role.PLANNER, Role.ASSISTANT]),
]

# The same, only while the « Mariages » module is on (weddings, their tasks, tickets).
WEDDING_PERMISSIONS: list[type[BasePermission]] = [*PERMISSIONS, WeddingsEnabled]

# Centralized calendar (§4.3, §12): the storekeeper reads the logistics too, never amounts.
CALENDAR_ROLES = (
    Role.OWNER,
    Role.PLANNER,
    Role.ASSISTANT,
    Role.ACCOUNTANT,
    Role.STOREKEEPER,
)
