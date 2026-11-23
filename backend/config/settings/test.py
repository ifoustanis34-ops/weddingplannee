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

# Anti-bot: off by default in tests (its own tests turn it on); no global request limit.
ANTIBOT_ENABLED = False
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {"anon": "100000/min", "user": "100000/min"},
}
