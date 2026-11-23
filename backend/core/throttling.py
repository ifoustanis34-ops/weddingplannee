"""Request limits for every API call (anti-bot, 20/11/2026), on top of the per-form limits.

A person never reaches them; a script scraping the API or hammering a public page does. Keyed
by the visitor's real address (``audit.client_ip``) or by the account. Rates come from the
settings (``API_RATE_ANON``, ``API_RATE_USER``).
"""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from .audit import client_ip


class VisitorThrottle(AnonRateThrottle):
    scope = "anon"

    def get_ident(self, request: Request) -> str:
        return client_ip(request) or "unknown"


class AccountThrottle(UserRateThrottle):
    scope = "user"

    def get_ident(self, request: Request) -> str:
        return client_ip(request) or "unknown"
