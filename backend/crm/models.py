"""Clients of the agency (reservations-stock.md §4.4): one record per client, no pipeline."""

from __future__ import annotations

import re
from typing import Any

from django.contrib.postgres.indexes import GinIndex
from django.db import models

from core.models import TenantModel


def phone_key(phone: str) -> str:
    """Comparable form of a phone number for duplicate detection.

    Keeps the last 9 digits so `+225 07 08 12 34 56`, `00225 0708123456` and `07 08 12 34 56`
    match.
    """
    digits = re.sub(r"\D", "", phone or "")
    return digits[-9:] if len(digits) >= 9 else digits


class Client(TenantModel):
    """A couple, a family, a company or another agency that orders from the agency."""

    name = models.CharField(max_length=160)
    company = models.CharField(max_length=160, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    phone_key = models.CharField(max_length=16, blank=True, editable=False)
    phone_alt = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    preferences = models.TextField(blank=True)
    # Archived clients leave the list but keep their quotes, contracts and history.
    is_archived = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    class Meta(TenantModel.Meta):
        ordering = ["name"]
        indexes = [
            models.Index(fields=["organization", "phone_key"], name="crm_client_phone_idx"),
            models.Index(fields=["organization", "email"], name="crm_client_email_idx"),
            GinIndex(
                name="crm_client_name_trgm",
                fields=["name"],
                opclasses=["gin_trgm_ops"],
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.phone_key = phone_key(self.phone)
        self.email = (self.email or "").strip().lower()
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "phone" in update_fields:
            kwargs["update_fields"] = {*update_fields, "phone_key"}
        super().save(*args, **kwargs)
