"""Anti-bot for the public forms (20/11/2026): sign-in, sign-up, forgotten password.

Two checks a person never notices, on top of the attempt limits (``core.ratelimit``):

- a honeypot: the field ``website`` is hidden from people; robots filling every field fill it;
- a form token (``GET /auth/form-token``): signed with the secret key and dated. A request sent
  without first opening the form, faster than a person types, or hours later is refused.

``ANTIBOT_ENABLED`` turns both off (tests, scripts); ``ANTIBOT_MIN_SECONDS`` is the shortest
time to fill the sign-up form.
"""

from __future__ import annotations

from collections.abc import Mapping
from time import time
from typing import Any

from django.conf import settings
from django.core import signing

from .exceptions import BusinessError

SALT = "wedivo.antibot"
HONEYPOT = "website"
TOKEN = "form_token"  # noqa: S105 - a field name, not a secret
MAX_AGE = 2 * 3600

REFUSED = "Envoi refusé. Rechargez la page puis réessayez."
TOO_FAST = "Envoi trop rapide. Patientez une seconde puis réessayez."


def issue() -> str:
    return signing.TimestampSigner(salt=SALT).sign_object({"v": 1})


def check(data: Any, *, min_seconds: float = 0) -> None:
    """Raise ``BusinessError("bot_suspected")`` when the request does not look human."""
    if not getattr(settings, "ANTIBOT_ENABLED", True):
        return
    data = data if isinstance(data, Mapping) else {}
    if str(data.get(HONEYPOT) or "").strip():
        raise BusinessError("bot_suspected", REFUSED)
    token = str(data.get(TOKEN) or "")
    signer = signing.TimestampSigner(salt=SALT)
    try:
        signer.unsign_object(token, max_age=MAX_AGE)
        _, stamp, _ = token.rsplit(":", 2)
        issued = signing.b62_decode(stamp)
    except (signing.BadSignature, ValueError):
        raise BusinessError("bot_suspected", REFUSED) from None
    if time() - issued < min_seconds:
        raise BusinessError("bot_suspected", TOO_FAST)
