from __future__ import annotations

from typing import Any

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from finance.permissions import role_of

from . import services


class AlertListView(APIView):
    """Open alerts the role may see, most urgent first (the bell and the dashboard)."""

    open_to_field_roles = True

    @extend_schema(responses={200: OpenApiResponse(OpenApiTypes.OBJECT)})
    def get(self, request: Request) -> Response:
        services.refresh_if_stale()
        rows: list[dict[str, Any]] = services.sorted_open(role_of(request), filter_role=True)
        return Response({"count": len(rows), "results": rows})


class AlertDismissView(APIView):
    """« Marquer comme traitée »."""

    open_to_field_roles = True

    @extend_schema(request=None, responses={200: OpenApiResponse(OpenApiTypes.OBJECT)})
    def post(self, request: Request, pk: str) -> Response:
        alert = services.open_alerts().filter(pk=pk).first()
        # Another agency's alert, or one this role must not see: it does not exist (404).
        if alert is None or not services.visible_to(alert.kind, role_of(request)):
            raise NotFound("Cette alerte n’existe plus.")
        services.dismiss(alert, user=request.user)  # type: ignore[arg-type]
        return Response(services.as_dict(alert), status=status.HTTP_200_OK)
