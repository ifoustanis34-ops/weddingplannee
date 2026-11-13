from .base import *  # noqa: F403

DEBUG = True
TENANT_HEADER_ENABLED = True
JWT_COOKIE_SECURE = False
ALLOWED_HOSTS = ["*"]
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Serve static files from app directories without a collectstatic run.
WHITENOISE_AUTOREFRESH = True
