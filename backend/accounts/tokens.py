"""JWT session in httpOnly cookies, with refresh rotation and Redis revocation (db 2)."""

from __future__ import annotations

import time

from django.conf import settings
from django.core.cache import caches
from django.http import HttpResponse
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from core.exceptions import BusinessError

from .models import User

SESSION_EXPIRED = BusinessError(
    "session_expired", "Votre session a expiré. Reconnectez-vous.", status_code=401
)


def _revocation_key(jti: str) -> str:
    return f"jwt:revoked:{jti}"


def issue_tokens(user: User) -> RefreshToken:
    return RefreshToken.for_user(user)


def revoke(refresh: RefreshToken) -> None:
    ttl = max(1, int(refresh["exp"]) - int(time.time()))
    caches["locks"].set(_revocation_key(str(refresh["jti"])), 1, timeout=ttl)


def is_revoked(refresh: RefreshToken) -> bool:
    return bool(caches["locks"].get(_revocation_key(str(refresh["jti"]))))


def parse_refresh(raw: str | None) -> RefreshToken:
    if not raw:
        raise SESSION_EXPIRED
    try:
        refresh = RefreshToken(raw)  # type: ignore[arg-type]
    except TokenError as exc:
        raise SESSION_EXPIRED from exc
    if is_revoked(refresh):
        raise SESSION_EXPIRED
    return refresh


def rotate(raw: str | None) -> tuple[User, RefreshToken]:
    """Exchange a refresh token for a new pair; the old one can never be reused."""
    refresh = parse_refresh(raw)
    user = User.objects.filter(pk=refresh["user_id"], is_active=True).first()
    if user is None:
        raise SESSION_EXPIRED
    revoke(refresh)
    return user, issue_tokens(user)


def set_auth_cookies(response: HttpResponse, refresh: RefreshToken) -> None:
    common = {
        "httponly": True,
        "secure": settings.JWT_COOKIE_SECURE,
        "samesite": "Lax",
        "domain": settings.JWT_COOKIE_DOMAIN,
    }
    response.set_cookie(
        settings.JWT_ACCESS_COOKIE,
        str(refresh.access_token),
        max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        path="/api/",
        **common,
    )
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE,
        str(refresh),
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path="/api/v1/auth/",
        **common,
    )


def clear_auth_cookies(response: HttpResponse) -> None:
    domain = settings.JWT_COOKIE_DOMAIN
    response.delete_cookie(settings.JWT_ACCESS_COOKIE, path="/api/", domain=domain)
    response.delete_cookie(settings.JWT_REFRESH_COOKIE, path="/api/v1/auth/", domain=domain)
