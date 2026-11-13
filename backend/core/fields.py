from __future__ import annotations

from typing import Any

from django.db import models
from rest_framework import serializers

from .tenant import get_current_organization


class TenantPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):  # type: ignore[type-arg]
    """Primary key of a tenant model, resolved in the active organization only.

    The queryset is built at validation time (the request's tenant context), never at import:
    an id belonging to another organization is simply « not found ».
    """

    def __init__(
        self, model: type[models.Model], filters: dict[str, Any] | None = None, **kwargs: Any
    ) -> None:
        self.model = model
        self.filters = filters or {}
        kwargs.setdefault("queryset", model.all_tenants.none())  # type: ignore[attr-defined]
        super().__init__(**kwargs)

    def get_queryset(self) -> models.QuerySet[Any]:
        if get_current_organization() is None:  # schema generation, no request
            return self.model.all_tenants.none()  # type: ignore[attr-defined,no-any-return]
        return self.model.objects.filter(**self.filters)  # type: ignore[attr-defined,no-any-return]
