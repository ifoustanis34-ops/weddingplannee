import logging
from typing import Any

from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from crm import selectors as crm_selectors
from quotes import selectors as quote_selectors
from quotes.models import Quote

logger = logging.getLogger(__name__)


def _check_database() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except Exception:
        logger.exception("Health check: database unavailable")
        return False


def _check_cache() -> bool:
    try:
        cache.set("health:ping", "pong", timeout=5)
        return bool(cache.get("health:ping") == "pong")
    except Exception:
        logger.exception("Health check: cache unavailable")
        return False


class HealthView(APIView):
    """Liveness and dependency check used by the frontend, Nginx and monitoring."""

    permission_classes = [AllowAny]
    authentication_classes: list[type] = []

    @extend_schema(
        responses=inline_serializer(
            name="Health",
            fields={
                "status": serializers.CharField(),
                "database": serializers.CharField(),
                "cache": serializers.CharField(),
            },
        )
    )
    def get(self, request: Request) -> Response:
        database_ok = _check_database()
        cache_ok = _check_cache()
        healthy = database_ok and cache_ok
        return Response(
            {
                "status": "ok" if healthy else "degraded",
                "database": "ok" if database_ok else "error",
                "cache": "ok" if cache_ok else "error",
            },
            status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )


SEARCH_LIMIT = 5


class SearchView(APIView):
    """Ctrl+K palette (CLAUDE.md §7.10): clients and quotes of the current organization.

    Every member may read clients and quotes (§11), so the default tenant permission applies.
    """

    @extend_schema(
        parameters=[OpenApiParameter("q", str, required=True)],
        responses=inline_serializer(
            "SearchResults",
            {
                "clients": inline_serializer(
                    "SearchClient",
                    {
                        "id": serializers.UUIDField(),
                        "name": serializers.CharField(),
                        "company": serializers.CharField(),
                    },
                    many=True,
                ),
                "quotes": inline_serializer(
                    "SearchQuote",
                    {
                        "id": serializers.UUIDField(),
                        "number": serializers.CharField(),
                        "client_name": serializers.CharField(),
                        "status": serializers.CharField(),
                        "total": serializers.IntegerField(),
                    },
                    many=True,
                ),
            },
        ),
    )
    def get(self, request: Request) -> Response:
        term = request.query_params.get("q", "").strip()[:80]
        if len(term) < 2:
            return Response({"clients": [], "quotes": []})
        clients = crm_selectors.search(crm_selectors.active_clients(), term)[:SEARCH_LIMIT]
        quotes = quote_selectors.search(
            Quote.objects.filter(is_template=False).select_related("client"), term
        )[:SEARCH_LIMIT]
        return Response(
            {
                "clients": [{"id": c.id, "name": c.name, "company": c.company} for c in clients],
                "quotes": [
                    {
                        "id": q.id,
                        "number": q.number,
                        "client_name": q.client.name if q.client else "",
                        "status": q.status,
                        "total": q.total,
                    }
                    for q in quotes
                ],
            }
        )


class ExportView(APIView):
    """« Télécharger » (PDF, CSV, Excel) of any screen's list: `core.exports`."""

    open_to_field_roles = True  # the storekeeper downloads his stock and movements

    @extend_schema(
        parameters=[OpenApiParameter("output", enum=["pdf", "csv", "xlsx"], default="pdf")],
        responses={200: None},
    )
    def get(self, request: Request, kind: str) -> Any:
        from core import audit
        from core.exceptions import BusinessError
        from core.exports import export
        from core.tenant import require_current_organization
        from finance import reports

        membership = getattr(request, "membership", None)
        role = membership.role if membership is not None else None
        chosen = export(kind)
        if not chosen.roles(role):
            raise BusinessError(
                "forbidden", "Votre rôle n’a pas accès à ces données.", status_code=403
            )
        output = request.query_params.get("output", "pdf")
        if output not in ("pdf", "csv", "xlsx"):
            raise BusinessError("invalid", "Choisissez PDF, CSV ou Excel.")
        table = chosen.build(request.query_params, role)
        response = reports.respond(table, output, f"{chosen.name}-{timezone.localdate():%Y%m%d}")
        audit.record(
            "export.downloaded",
            require_current_organization(),
            request=request,
            changes={"kind": kind, "output": output, "rows": len(table["rows"])},
        )
        return response
