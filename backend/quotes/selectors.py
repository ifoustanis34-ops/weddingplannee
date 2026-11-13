from __future__ import annotations

from datetime import datetime, timedelta
from statistics import median

from django.db.models import Q, QuerySet, Sum
from django.db.models.functions import Coalesce

from .models import Quote


def search(queryset: QuerySet[Quote], term: str) -> QuerySet[Quote]:
    """Quotes whose number or client name contains ``term``."""
    term = term.strip()
    if not term:
        return queryset
    return queryset.filter(Q(number__icontains=term) | Q(client__name__icontains=term))


def stats(now: datetime, month_start: datetime) -> dict[str, int | float | None]:
    """Figures of the quote list tiles (complement §16).

    - creation time: median minutes between the draft and its sending, quotes sent in 30 days;
    - acceptance rate: accepted ÷ (accepted + refused + expired) over 90 days.
    """
    quotes = Quote.objects.filter(is_template=False)
    durations = sorted(
        (sent_at - created_at).total_seconds() / 60
        for created_at, sent_at in quotes.filter(sent_at__gte=now - timedelta(days=30)).values_list(
            "created_at", "sent_at"
        )
    )
    window = now - timedelta(days=90)
    accepted = quotes.filter(accepted_at__gte=window).count()
    refused = quotes.filter(refused_at__gte=window).count()
    expired = quotes.filter(status=Quote.Status.EXPIRED, valid_until__gte=window.date()).count()
    decided = accepted + refused + expired
    return {
        "median_creation_minutes": round(median(durations)) if durations else None,
        "sent_this_month": quotes.filter(sent_at__gte=month_start).count(),
        "acceptance_rate": round(accepted * 100 / decided) if decided else None,
        "pending_amount": int(
            quotes.filter(status=Quote.Status.SENT).aggregate(total=Coalesce(Sum("total"), 0))[
                "total"
            ]
        ),
    }
