"""Drop the cached financial summary and dashboard whenever what they show changes."""

from __future__ import annotations

from typing import Any

from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from contracts.models import Contract, Payment, PaymentSchedule
from crm.models import Client
from documents.models import OrganizationBranding
from events.models import Task, Wedding
from quotes.models import Quote
from reservations.models import Reservation, ReservationLine, ReservationPayment
from stock.models import Item, ItemUnit, Maintenance, StockMovement
from vendors.models import VendorAssignment

from .models import Expense, ExpenseCategory

WATCHED = (
    Payment,
    Contract,
    PaymentSchedule,
    Expense,
    ExpenseCategory,
    Client,  # « Clients actifs » of the starter card
    Item,  # « Matériel aujourd'hui » and the stock alerts
    ItemUnit,
    Maintenance,
    StockMovement,
    Reservation,
    ReservationLine,
    ReservationPayment,
    Quote,
    Wedding,
    Task,
    VendorAssignment,
    OrganizationBranding,  # the starter card's « Ajouter votre logo »
)


def invalidate(organization_id: Any) -> None:
    from .dashboard import invalidate as invalidate_dashboard

    cache.delete_many(
        [f"org:{organization_id}:finance:summary", f"org:{organization_id}:alerts:refreshed"]
    )
    invalidate_dashboard(organization_id)  # every cached period at once


@receiver(post_save)
@receiver(post_delete)
def on_change(sender: type, instance: Any, **kwargs: Any) -> None:
    if sender in WATCHED and getattr(instance, "organization_id", None):
        invalidate(instance.organization_id)
