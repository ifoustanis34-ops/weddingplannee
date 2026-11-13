from .base import *  # noqa: F403

DEBUG = False
TENANT_HEADER_ENABLED = True
SIGNUP_RATE_LIMIT = 5
JWT_COOKIE_SECURE = False
ALLOWED_HOSTS = ["*"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "locks": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "locks"},
}
CELERY_TASK_ALWAYS_EAGER = True
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Serve static files from app directories without a collectstatic run.
WHITENOISE_AUTOREFRESH = True
