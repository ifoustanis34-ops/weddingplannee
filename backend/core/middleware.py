"""Resolve the organization of each request and scope the database transaction to it."""

from __future__ import annotations

from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse

from organizations.services import RESERVED_SLUGS, get_active_organization_by_slug

from .tenant import _current_org, tenant_context


def resolve_tenant_slug(request: HttpRequest) -> str | None:
    """`slug.wedivo.app` in production; `X-Organization: slug` header when enabled (dev, tests)."""
    host = request.get_host().split(":")[0].lower()
    base = settings.TENANT_BASE_DOMAIN.lower()
    if host.endswith(f".{base}"):
        subdomain = host[: -len(base) - 1]
        if subdomain and "." not in subdomain and subdomain not in RESERVED_SLUGS:
            return subdomain
    if settings.TENANT_HEADER_ENABLED:
        header = request.headers.get("X-Organization", "").strip().lower()
        if header:
            return header
    return None


class TenantMiddleware:
    """Sets ``request.organization`` and runs the request inside ``tenant_context``.

    Membership is checked by the DRF permission ``IsTenantMember``: the JWT cookie is only
    authenticated by DRF, after middlewares have run.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.organization = None  # type: ignore[attr-defined]
        slug = resolve_tenant_slug(request)
        if slug is None:
            return self.get_response(request)

        organization = get_active_organization_by_slug(slug)
        if organization is None:
            return JsonResponse(
                {
                    "code": "organization_not_found",
                    "message": "Cet espace n’existe pas ou a été désactivé.",
                    "fields": {},
                },
                status=404,
            )

        request.organization = organization  # type: ignore[attr-defined]
        with tenant_context(organization):
            response = self.get_response(request)
        # Defensive: never let the contextvar outlive the request.
        _current_org.set(None)
        return response
