from __future__ import annotations

import django_filters
from django.db.models import QuerySet

from .models import Client
from .selectors import search


class ClientFilter(django_filters.FilterSet):  # type: ignore[misc]
    search = django_filters.CharFilter(method="filter_search")
    archived = django_filters.BooleanFilter(field_name="is_archived")

    class Meta:
        model = Client
        fields = ["search", "archived"]

    def filter_search(self, queryset: QuerySet[Client], name: str, value: str) -> QuerySet[Client]:
        return search(queryset, value)
