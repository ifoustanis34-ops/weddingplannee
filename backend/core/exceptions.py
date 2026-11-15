"""Uniform API error format: ``{"code", "message", "fields"}`` (CLAUDE.md §9)."""

from __future__ import annotations

import logging
from typing import Any

from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

GENERIC_MESSAGES: dict[str, str] = {
    "not_authenticated": "Connectez-vous pour continuer.",
    "authentication_failed": "Votre session a expiré. Reconnectez-vous.",
    "permission_denied": "Vous n’avez pas accès à cette action.",
    "not_found": "Élément introuvable.",
    "method_not_allowed": "Action non disponible.",
    "throttled": "Trop de tentatives. Réessayez dans quelques minutes.",
    "parse_error": "Requête illisible.",
}


class BusinessError(exceptions.APIException):
    """Raise from services when a business rule refuses an action."""

    status_code: int = status.HTTP_400_BAD_REQUEST

    def __init__(
        self,
        code: str,
        message: str,
        fields: dict[str, list[str]] | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(detail=message, code=code)
        self.error_code = code
        self.fields = fields or {}
        if status_code is not None:
            self.status_code = status_code


class RateLimitedError(BusinessError):
    def __init__(self, retry_after: int) -> None:
        minutes = max(1, round(retry_after / 60))
        super().__init__(
            "rate_limited",
            f"Trop de tentatives. Réessayez dans {minutes} min.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
        self.retry_after = retry_after


def _flatten_fields(detail: Any) -> dict[str, list[str]]:
    if not isinstance(detail, dict):
        return {}
    fields: dict[str, list[str]] = {}
    for key, value in detail.items():
        if isinstance(value, list):
            fields[key] = [str(item) for item in value if not isinstance(item, dict)]
        elif isinstance(value, dict):
            for sub_key, sub_value in _flatten_fields(value).items():
                fields[f"{key}.{sub_key}"] = sub_value
        else:
            fields[key] = [str(value)]
    return fields


logger = logging.getLogger(__name__)

STORAGE_MESSAGE = (
    "Le fichier n’a pas pu être enregistré sur le serveur (espace de stockage indisponible). "
    "Réessayez plus tard ou prévenez l’administrateur de la plateforme."
)


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    response = drf_exception_handler(exc, context)
    if response is None:
        if isinstance(exc, OSError):
            # Photos, logos, receipts: the media folder is missing or not writable on the server
            # (feedback 15/11/2026). Said plainly instead of « Une erreur est survenue »; the
            # traceback stays in the logs for the administrator.
            logger.exception("File storage failed")
            return Response(
                {"code": "storage_unavailable", "message": STORAGE_MESSAGE, "fields": {}},
                status=503,
            )
        return None

    if isinstance(exc, BusinessError):
        body = {"code": exc.error_code, "message": str(exc.detail), "fields": exc.fields}
        if isinstance(exc, RateLimitedError):
            response["Retry-After"] = str(exc.retry_after)
    elif isinstance(exc, exceptions.ValidationError):
        fields = _flatten_fields(exc.detail)
        non_field = fields.pop("non_field_errors", [])
        if isinstance(exc.detail, list):
            non_field = [str(item) for item in exc.detail]
        message = non_field[0] if non_field else "Certains champs sont à corriger."
        body = {"code": "invalid", "message": message, "fields": fields}
    elif isinstance(exc, exceptions.APIException):
        codes = exc.get_codes()
        code = codes if isinstance(codes, str) else exc.default_code
        custom_code = getattr(exc, "error_code", None)
        code = str(custom_code or code)
        detail = str(exc.detail)
        message = GENERIC_MESSAGES.get(code, detail) if detail == exc.default_detail else detail
        body = {"code": code, "message": message, "fields": {}}
    else:  # pragma: no cover - DRF only returns responses for APIException subclasses
        return response

    response.data = body
    return response
