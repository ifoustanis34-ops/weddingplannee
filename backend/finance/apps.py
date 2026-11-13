from django.apps import AppConfig


class FinanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "finance"
    verbose_name = "Finances"

    def ready(self) -> None:
        from . import signals  # noqa: F401  (cache invalidation)
