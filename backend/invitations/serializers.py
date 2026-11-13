from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from rest_framework import serializers

from core.tenant import require_current_organization
from documents.palettes import PALETTES

from . import services
from .models import Guest, Ticket, TicketDesign


class TicketDesignSerializer(serializers.ModelSerializer[TicketDesign]):
    # Date and time as the agency reads them (« 2027-06-12T15:00 », its time zone), whatever
    # the zone of the browser: the ticket prints the same hour.
    starts_at_local = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = TicketDesign
        fields = ["id", *services.DESIGN_FIELDS, "starts_at_local", "updated_at"]
        read_only_fields = ["id", "starts_at", "updated_at"]

    def to_representation(self, instance: TicketDesign) -> dict[str, Any]:
        data = super().to_representation(instance)
        zone = ZoneInfo(require_current_organization().timezone)
        moment = instance.starts_at
        data["starts_at_local"] = (
            moment.astimezone(zone).strftime("%Y-%m-%dT%H:%M") if moment else None
        )
        return data

    def validate_starts_at_local(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            naive = datetime.strptime(value[:16], "%Y-%m-%dT%H:%M")
        except ValueError as exc:
            raise serializers.ValidationError("Date et heure au format AAAA-MM-JJTHH:MM.") from exc
        return naive.replace(tzinfo=ZoneInfo(require_current_organization().timezone))

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if "starts_at_local" in attrs:
            attrs["starts_at"] = attrs.pop("starts_at_local")
        return attrs

    def validate_palette(self, value: str) -> str:
        if value not in PALETTES:
            raise serializers.ValidationError("Palette inconnue.")
        return value

    def validate_categories(self, value: Any) -> list[str]:
        if not isinstance(value, list) or len(value) > 8:
            raise serializers.ValidationError("8 catégories au maximum.")
        cleaned = [str(item).strip()[:30] for item in value if str(item).strip()]
        return list(dict.fromkeys(cleaned))


class TicketSummarySerializer(serializers.ModelSerializer[Ticket]):
    url = serializers.SerializerMethodField()
    has_document = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            "id",
            "code",
            "status",
            "issued_at",
            "sent_at",
            "opened_at",
            "cancelled_at",
            "has_document",
            "url",
        ]

    def get_url(self, ticket: Ticket) -> str | None:
        # The guest's link, to copy into a message: only for a valid ticket.
        return services.public_url(ticket) if ticket.status == Ticket.Status.ACTIVE else None

    def get_has_document(self, ticket: Ticket) -> bool:
        return ticket.document_id is not None


def ticket_state(guest: Guest) -> str:
    """The list's single status (§6): non généré, généré, envoyé, ouvert, confirmé, annulé…"""
    ticket = guest.ticket
    if ticket is None:
        cancelled = getattr(guest, "has_cancelled", None)
        if cancelled is None:
            cancelled = guest.tickets.exclude(status=Ticket.Status.ACTIVE).exists()
        return "cancelled" if cancelled else "none"
    if guest.rsvp_status == Guest.Rsvp.ACCEPTED:
        return "confirmed"
    if guest.rsvp_status == Guest.Rsvp.DECLINED:
        return "declined"
    if ticket.opened_at:
        return "opened"
    if ticket.sent_at:
        return "sent"
    return "generated" if ticket.document_id else "none"


class GuestSerializer(serializers.ModelSerializer[Guest]):
    ticket = serializers.SerializerMethodField()
    ticket_state = serializers.SerializerMethodField()
    # Latest ticket whatever its status: a cancelled ticket can be reissued from the list.
    last_ticket_id = serializers.SerializerMethodField()
    seats = serializers.IntegerField(min_value=1, max_value=50, default=1)

    class Meta:
        model = Guest
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "seats",
            "category",
            "table",
            "notes",
            "rsvp_status",
            "rsvp_at",
            "ticket",
            "ticket_state",
            "last_ticket_id",
        ]
        read_only_fields = ["id", "rsvp_status", "rsvp_at"]

    def get_ticket(self, guest: Guest) -> dict[str, Any] | None:
        ticket = guest.ticket
        return TicketSummarySerializer(ticket).data if ticket else None

    def get_ticket_state(self, guest: Guest) -> str:
        return ticket_state(guest)

    def get_last_ticket_id(self, guest: Guest) -> str | None:
        ticket = guest.ticket
        if ticket is not None:
            return str(ticket.pk)
        last = getattr(guest, "last_ticket", None)
        if last is None and not hasattr(guest, "last_ticket"):
            found = guest.tickets.order_by("-number").values_list("pk", flat=True).first()
            last = str(found) if found else None
        return str(last) if last else None


class GenerateSerializer(serializers.Serializer[Any]):
    guests = serializers.ListField(child=serializers.UUIDField(), required=False, max_length=2000)
    all = serializers.BooleanField(default=False)


class ImportSerializer(serializers.Serializer[Any]):
    file = serializers.FileField()


class RsvpSerializer(serializers.Serializer[Any]):
    accepted = serializers.BooleanField()


class TicketPreviewSerializer(serializers.Serializer[Any]):
    wedding = serializers.UUIDField()
    draft = serializers.DictField(required=False, default=dict)
