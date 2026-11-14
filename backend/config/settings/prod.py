from .base import *  # noqa: F403
from .base import env

DEBUG = False

# The key also signs the JWT (HS256): require a long random value in production.
if len(SECRET_KEY) < 50:
    raise RuntimeError("DJANGO_SECRET_KEY must be at least 50 random characters in production.")

# Signs every ticket's QR code: refuse to start without a long random master key.
if len(DOCUMENTS_MASTER_KEY) < 32:
    raise RuntimeError("DOCUMENTS_MASTER_KEY must be at least 32 random characters in production.")
TICKET_LINKS_ON_SUBDOMAIN = env.bool("TICKET_LINKS_ON_SUBDOMAIN", default=True)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# The space comes from the subdomain (slug.<TENANT_BASE_DOMAIN>) when there is one, otherwise
# from the X-Organization header the app sends: Wedivo then works on a single address
# (feedback 14/11/2026: « Vous n'avez pas accès à cet espace » on every action online).
# Safe: every request still needs an active membership of that space (IsTenantMember) and the
# data stays isolated by RLS. TENANT_HEADER_ENABLED=false keeps subdomains only.
TENANT_HEADER_ENABLED = env.bool("TENANT_HEADER_ENABLED", default=True)
# The session cookie is always Secure: the site must be served over HTTPS.
JWT_COOKIE_SECURE = True
