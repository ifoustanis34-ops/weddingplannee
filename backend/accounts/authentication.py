from __future__ import annotations

from typing import Any

from django.conf import settings
from django.http import HttpRequest
from rest_framework import exceptions
from rest_framework.authentication import CSRFCheck
from rest_framework.request import Request
from rest_framework_simplejwt.authentication import JWTAuthentication


class CSRFFailed(exceptions.PermissionDenied):
    default_detail = "Jeton de sécurité manquant ou expiré. Rechargez la page puis réessayez."
    default_code = "csrf_failed"


class CookieJWTAuthentication(JWTAuthentication):
    """Reads the access token from the httpOnly cookie (or a Bearer header for API clients).

    Cookie-authenticated unsafe requests must carry the CSRF token, like Django sessions.
    """

    def authenticate(self, request: Request) -> tuple[Any, Any] | None:
        header = self.get_header(request)
        if header is not None:
            return super().authenticate(request)

        raw = request.COOKIES.get(settings.JWT_ACCESS_COOKIE)
        if not raw:
            return None
        validated = self.get_validated_token(raw.encode())
        user = self.get_user(validated)
        self._enforce_csrf(request)
        return user, validated

    def _enforce_csrf(self, request: Request) -> None:
        def dummy_get_response(_: HttpRequest) -> None:  # pragma: no cover
            return None

        check = CSRFCheck(dummy_get_response)  # type: ignore[arg-type]
        check.process_request(request)
        rejection = check.process_view(request, None, (), {})  # type: ignore[arg-type]
        if rejection is not None:
            raise CSRFFailed()
