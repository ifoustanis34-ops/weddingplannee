"""Local time of an organization (CLAUDE.md §6: one time zone per organization)."""

from __future__ import annotations

import zoneinfo

from .models import Organization

DEFAULT_TZ = "Africa/Abidjan"


def org_tz(organization: Organization) -> zoneinfo.ZoneInfo:
    try:
        return zoneinfo.ZoneInfo(organization.timezone)
    except zoneinfo.ZoneInfoNotFoundError:
        return zoneinfo.ZoneInfo(DEFAULT_TZ)
