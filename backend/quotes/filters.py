from __future__ import annotations

import django_filters

from .models import Quote


class QuoteFilter(django_filters.FilterSet):  # type: ignore[misc]
    # Plain UUID filter: a model choice filter would build a Client queryset outside any tenant.
    client = django_filters.UUIDFilter(field_name="client_id")
    status = django_filters.MultipleChoiceFilter(choices=Quote.Status.choices)
    is_template = django_filters.BooleanFilter()

    class Meta:
        model = Quote
        fields = ["client", "status", "is_template"]
