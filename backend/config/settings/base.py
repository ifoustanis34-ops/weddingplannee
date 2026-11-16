"""Base settings shared by every environment."""

from datetime import timedelta
from pathlib import Path

import environ
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR.parent / ".env", overwrite=False)

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # Third party
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    "django_filters",
    # Local
    "core",
    "organizations",
    "accounts",
    "crm",
    "catalog",
    "quotes",
    "contracts",
    "events",
    "vendors",
    "documents",
    "invitations",
    "finance",
    "alerts",
    "stock",
    "reservations",
    "staff",
    "notifications",
    "platform_admin",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.TenantMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = env("REDIS_URL", default="redis://redis:6379")

# Redis db 1: cache. Redis db 2 is reserved for rate limits, token revocation and locks.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"{REDIS_URL}/1",
        "KEY_PREFIX": "wedivo",
    },
    "locks": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": f"{REDIS_URL}/2",
        "KEY_PREFIX": "wedivo",
    },
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["accounts.authentication.CookieJWTAuthentication"],
    # Every endpoint is tenant-scoped unless it says otherwise.
    "DEFAULT_PERMISSION_CLASSES": ["core.permissions.IsTenantMember"],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.DefaultCursorPagination",
    "EXCEPTION_HANDLER": "core.exceptions.exception_handler",
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}
JWT_ACCESS_COOKIE = "wedivo_access"
JWT_REFRESH_COOKIE = "wedivo_refresh"
JWT_COOKIE_SECURE = env.bool("JWT_COOKIE_SECURE", default=not DEBUG)
# ".wedivo.app" in production so the session follows the user across company subdomains.
JWT_COOKIE_DOMAIN = env("JWT_COOKIE_DOMAIN", default=None)

# Multi-tenant: "slug.wedivo.app". The X-Organization header is a dev/test convenience only.
TENANT_BASE_DOMAIN = env("TENANT_BASE_DOMAIN", default="wedivo.app")
TENANT_HEADER_ENABLED = env.bool("TENANT_HEADER_ENABLED", default=DEBUG)

FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:8090")

# Tickets (docs/specs/devis-billets.md §7): the HMAC key of each organization is derived (HKDF)
# from this master key. Required in production; dev and tests fall back to a fixed value.
DOCUMENTS_MASTER_KEY = env("DOCUMENTS_MASTER_KEY", default="")
# Ticket links on the agency subdomain (https://{slug}.wedivo.app/t/…) or on FRONTEND_URL (dev).
TICKET_LINKS_ON_SUBDOMAIN = env.bool("TICKET_LINKS_ON_SUBDOMAIN", default=False)

# Account creations per IP and per hour. Raised in local dev to replay end-to-end journeys.
SIGNUP_RATE_LIMIT = env.int("SIGNUP_RATE_LIMIT", default=5)
# Every agency gets every feature whatever its offer (product decision, Nov. 2026): the offers'
# limits (users) are not enforced. Future modules may be reserved to an offer later.
ALL_FEATURES_INCLUDED = env.bool("ALL_FEATURES_INCLUDED", default=True)
# Django admin address, e.g. "gestion-7f3a/" ; empty = off (production default).
DJANGO_ADMIN_URL = env.str("DJANGO_ADMIN_URL", default="admin/" if DEBUG else "")

# Web Push of the PWA (feedback 13/11/2026). Keys from `manage.py generate_vapid_keys`; without
# them no notification is sent and the app hides the switch.
VAPID_PUBLIC_KEY = env("VAPID_PUBLIC_KEY", default="")
VAPID_PRIVATE_KEY = env("VAPID_PRIVATE_KEY", default="")
VAPID_SUBJECT = env("VAPID_SUBJECT", default="mailto:support@wedivo.app")

# Presentation mode (feedback 16/11/2026): the app plays the journeys of a fictitious agency and
# switches between its roles without a password. Off unless asked, and only in these spaces.
DEMO_MODE = env.bool("DEMO_MODE", default=False)
DEMO_ORGANIZATIONS = env.list("DEMO_ORGANIZATIONS", default=["maison-elegance"])
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Wedivo <no-reply@wedivo.app>")

SPECTACULAR_SETTINGS = {
    "TITLE": "Wedivo API",
    "DESCRIPTION": "API de la plateforme Wedivo pour wedding planners.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "QuoteStatusEnum": "quotes.models.Quote.Status",
        "ContractStatusEnum": "contracts.models.Contract.Status",
        "PaymentMethodEnum": "contracts.models.Payment.Method",
    },
}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# Celery: Redis db 0 is the broker.
CELERY_BROKER_URL = f"{REDIS_URL}/0"
CELERY_RESULT_BACKEND = None
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULE: dict[str, dict[str, object]] = {
    "expire-quotes": {
        "task": "quotes.tasks.expire_quotes",
        "schedule": crontab(hour=1, minute=0),
    },
    "alert-digest": {
        "task": "alerts.tasks.send_daily_digests",
        "schedule": crontab(hour=7, minute=30),
    },
    "task-alerts": {
        "task": "events.tasks.notify_due_tasks",
        "schedule": crontab(hour=8, minute=0),
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
    # WeasyPrint logs every rendering step at INFO.
    "loggers": {"weasyprint": {"level": "WARNING"}, "fontTools": {"level": "WARNING"}},
}
