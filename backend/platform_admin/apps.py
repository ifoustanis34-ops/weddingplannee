from django.apps import AppConfig


class PlatformAdminConfig(AppConfig):
    """Console of the Wedivo team (« super-admin »): every agency, every account."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "platform_admin"
    verbose_name = "Console plateforme"
