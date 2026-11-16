from .base import *  # noqa: F403

DEBUG = True
TENANT_HEADER_ENABLED = True
JWT_COOKIE_SECURE = False
ALLOWED_HOSTS = ["*"]
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Serve static files from app directories without a collectstatic run.
WHITENOISE_AUTOREFRESH = True

# Presentation mode on in development: the demo agency (renamed copies included).
DEMO_MODE = env.bool("DEMO_MODE", default=True)
DEMO_ORGANIZATIONS = env.list("DEMO_ORGANIZATIONS", default=["maison-elegance", "canopy-houses"])
