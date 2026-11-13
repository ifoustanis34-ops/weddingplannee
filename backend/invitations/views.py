"""Guests, tickets and the guest's public page (docs/specs/devis-billets.md §6, §7)."""

from __future__ import annotations

from typing import Any, cast

from django.db.models import Exists, OuterRef, Prefetch, QuerySet, Subquery
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.views import PublicAPIView
from core import audit, ratelimit
from core.audit import client_ip
from core.exceptions import BusinessError
from core.tenant import require_current_organization, tenant_context
from events.models import Wedding
from events.permissions import WEDDING_PERMISSIONS

from . import services, tasks
from .models import Guest, Ticket, TicketDesign
from .serializers import (
    GenerateSerializer,
    GuestSerializer,
    ImportSerializer,
    RsvpSerializer,
    TicketDesignSerializer,
    TicketPreviewSerializer,
    TicketSummarySerializer,
)


def _guests() -> QuerySet[Guest]:
    queryset = Guest.objects.prefetch_related(
        Prefetch(
            "tickets",
            queryset=Ticket.objects.filter(status=Ticket.Status.ACTIVE),
            to_attr="active_tickets",
        )
    ).annotate(
        has_cancelled=Exists(
            Ticket.objects.filter(guest=OuterRef("pk")).exclude(status=Ticket.Status.ACTIVE)
        ),
        last_ticket=Subquery(
            Ticket.objects.filter(guest=OuterRef("pk")).order_by("-number").values("pk")[:1]
        ),
    )
    return cast(QuerySet[Guest], queryset)


class WeddingScoped(APIView):
    permission_classes = WEDDING_PERMISSIONS

    def wedding(self) -> Wedding:
        return cast(Wedding, get_object_or_404(Wedding.objects.all(), pk=self.kwargs["pk"]))

    @property
    def user(self) -> User:
        return self.request.user  # type: ignore[return-value]


class TicketDesignView(WeddingScoped):
    @extend_schema(responses=TicketDesignSerializer)
    def get(self, request: Request, pk: str) -> Response:
        return Response(TicketDesignSerializer(services.get_design(self.wedding())).data)

    @extend_schema(request=TicketDesignSerializer, responses=TicketDesignSerializer)
    def patch(self, request: Request, pk: str) -> Response:
        design = services.get_design(self.wedding())
        serializer = TicketDesignSerializer(design, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_design(design, dict(serializer.validated_data))
        return Response(TicketDesignSerializer(design).data)


class GuestListView(generics.ListCreateAPIView[Guest]):
    permission_classes = WEDDING_PERMISSIONS
    serializer_class = GuestSerializer
    pagination_class = None

    def get_queryset(self) -> QuerySet[Guest]:
        if getattr(self, "swagger_fake_view", False):
            return Guest.all_tenants.none()
        wedding = get_object_or_404(Wedding.objects.all(), pk=self.kwargs["pk"])
        return _guests().filter(wedding=wedding)

    def perform_create(self, serializer: GuestSerializer) -> None:  # type: ignore[override]
        wedding = get_object_or_404(Wedding.objects.all(), pk=self.kwargs["pk"])
        serializer.instance = services.create_guest(
            wedding, dict(serializer.validated_data), user=self.request.user  # type: ignore[arg-type]
        )


class GuestDetailView(generics.RetrieveUpdateDestroyAPIView[Guest]):
    permission_classes = WEDDING_PERMISSIONS
    serializer_class = GuestSerializer

    def get_queryset(self) -> QuerySet[Guest]:
        if getattr(self, "swagger_fake_view", False):
            return Guest.all_tenants.none()
        return _guests()

    def perform_update(self, serializer: GuestSerializer) -> None:  # type: ignore[override]
        services.update_guest(serializer.instance, dict(serializer.validated_data))  # type: ignore[arg-type]

    def perform_destroy(self, instance: Guest) -> None:
        services.delete_guest(instance)


class GuestImportView(WeddingScoped):
    @extend_schema(request=ImportSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request: Request, pk: str) -> Response:
        serializer = ImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = services.import_guests(
            self.wedding(), serializer.validated_data["file"], user=self.user
        )
        return Response({"created": result.created, "skipped": result.skipped})


class GenerateTicketsView(WeddingScoped):
    """« Générer » (a selection) or « Générer tous les billets »: a batch with its progress."""

    @extend_schema(request=GenerateSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request: Request, pk: str) -> Response:
        serializer = GenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        wedding = self.wedding()
        guests = Guest.objects.filter(wedding=wedding)
        if not serializer.validated_data["all"]:
            guests = guests.filter(pk__in=serializer.validated_data.get("guests", []))
        guest_ids = [str(value) for value in guests.values_list("pk", flat=True)]
        if not guest_ids:
            raise BusinessError("no_guests", "Choisissez au moins un invité.")
        organization_id = str(require_current_organization().pk)
        batch = tasks.start_batch(organization_id, str(wedding.pk), guest_ids, str(self.user.pk))
        audit.record(
            "tickets.generated", wedding, request=request, changes={"guests": len(guest_ids)}
        )
        return Response(
            {"batch": batch, **(tasks.get_progress(organization_id, batch) or {})},
            status=status.HTTP_202_ACCEPTED,
        )


class TicketBatchView(APIView):
    permission_classes = WEDDING_PERMISSIONS

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request: Request, batch: str) -> Response:
        progress = tasks.get_progress(str(require_current_organization().pk), batch)
        if progress is None:
            raise Http404
        return Response({"batch": batch, **progress})


class ExportTicketsView(WeddingScoped):
    """All the active tickets: one PDF, or a ZIP of one PDF per guest."""

    @extend_schema(responses={(200, "application/pdf"): bytes, (200, "application/zip"): bytes})
    def get(self, request: Request, pk: str) -> HttpResponse:
        wedding = self.wedding()
        tickets = list(
            Ticket.objects.select_related("guest", "wedding")
            .filter(wedding=wedding, status=Ticket.Status.ACTIVE)
            .exclude(document=None)
            .order_by("number")
        )
        if not tickets:
            raise BusinessError("no_tickets", "Générez d’abord les billets.")
        kind = request.query_params.get("type", "pdf")
        if kind == "zip":
            response = HttpResponse(services.export_zip(tickets), content_type="application/zip")
            response["Content-Disposition"] = 'attachment; filename="billets.zip"'
        else:
            response = HttpResponse(services.export_pdf(tickets), content_type="application/pdf")
            response["Content-Disposition"] = 'attachment; filename="billets.pdf"'
        audit.record("tickets.exported", wedding, request=request, changes={"type": kind})
        return response


class TicketActionView(APIView):
    permission_classes = WEDDING_PERMISSIONS

    def ticket(self) -> Ticket:
        found = get_object_or_404(
            Ticket.objects.select_related("guest", "wedding"), pk=self.kwargs["pk"]
        )
        return cast(Ticket, found)


class TicketPdfView(TicketActionView):
    @extend_schema(responses={(200, "application/pdf"): bytes})
    def get(self, request: Request, pk: str) -> HttpResponse:
        ticket = self.ticket()
        response = HttpResponse(services.pdf_bytes(ticket), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{ticket.code}.pdf"'
        return response


class CancelTicketView(TicketActionView):
    @extend_schema(request=None, responses=TicketSummarySerializer)
    def post(self, request: Request, pk: str) -> Response:
        ticket = services.cancel_ticket(self.ticket())
        audit.record("ticket.cancelled", ticket, request=request)
        return Response(TicketSummarySerializer(ticket).data)


class ReissueTicketView(TicketActionView):
    @extend_schema(request=None, responses=TicketSummarySerializer)
    def post(self, request: Request, pk: str) -> Response:
        old = self.ticket()
        fresh = services.reissue_ticket(old, user=request.user)  # type: ignore[arg-type]
        audit.record("ticket.reissued", old, request=request, changes={"new": fresh.code})
        return Response(TicketSummarySerializer(fresh).data, status=status.HTTP_201_CREATED)


class TicketPreviewView(APIView):
    """The design form's preview (§6): an example guest, the unsaved design, a PNG."""

    permission_classes = WEDDING_PERMISSIONS

    @extend_schema(request=TicketPreviewSerializer, responses={(200, "image/png"): bytes})
    def post(self, request: Request) -> HttpResponse:
        from types import SimpleNamespace

        from documents import rendering

        serializer = TicketPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        wedding = get_object_or_404(Wedding.objects.all(), pk=serializer.validated_data["wedding"])
        design = services.get_design(wedding)
        draft = TicketDesignSerializer(
            design, data=serializer.validated_data["draft"], partial=True
        )
        draft.is_valid(raise_exception=True)
        values = {field: getattr(design, field) for field in services.DESIGN_FIELDS}
        values.update(draft.validated_data)
        snapshot = services.preview_snapshot(wedding, SimpleNamespace(**values))
        png, _ = rendering.cached_preview(
            snapshot["organization_id"], "ticket", snapshot, lambda: services.render(snapshot)
        )
        response = HttpResponse(png, content_type="image/png")
        response["Cache-Control"] = "private, no-store"
        return response


# --- Guest's public page (/t/{token}) ---------------------------------------------------------

PUBLIC_LIMIT, PUBLIC_WINDOW = 60, 60


def _private(response: HttpResponse) -> HttpResponse:
    response["X-Robots-Tag"] = "noindex, nofollow"
    response["Referrer-Policy"] = "no-referrer"
    response["Cache-Control"] = "private, max-age=60"
    return response


class PublicTicketMixin(PublicAPIView):
    def resolve(self, request: Request, token: str) -> Ticket:
        ratelimit.hit(
            "public-ticket",
            client_ip(request) or "unknown",
            limit=PUBLIC_LIMIT,
            window=PUBLIC_WINDOW,
        )
        ticket = services.find_by_token(token)
        if ticket is None:
            raise Http404
        return ticket


class PublicTicketView(PublicTicketMixin):
    """What the guest sees: never an entry, only their own ticket (§6, §11)."""

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request: Request, token: str) -> Response:
        ticket = self.resolve(request, token)
        with tenant_context(ticket.organization):
            if ticket.status == Ticket.Status.ACTIVE:
                services.mark_opened(ticket)
            design: TicketDesign = services.get_design(ticket.wedding)
            guest = ticket.guest
            data: dict[str, Any] = {
                "status": ticket.status,
                "code": ticket.code,
                "guest": {
                    "name": guest.name,
                    "seats": guest.seats,
                    "rsvp_status": guest.rsvp_status,
                },
                "couple": " & ".join(n for n in (design.partner_1, design.partner_2) if n),
                "starts_at": design.starts_at,
                "venue": design.venue,
                "address": design.address,
                "agency": services._agency()["trade_name"],
            }
        response = Response(data)
        response["X-Robots-Tag"] = "noindex, nofollow"
        response["Referrer-Policy"] = "no-referrer"
        return response


class PublicTicketImageView(PublicTicketMixin):
    @extend_schema(responses={(200, "image/png"): bytes})
    def get(self, request: Request, token: str) -> HttpResponse:
        ticket = self.resolve(request, token)
        with tenant_context(ticket.organization):
            return _private(HttpResponse(services.image(ticket), content_type="image/png"))


class PublicTicketPdfView(PublicTicketMixin):
    @extend_schema(responses={(200, "application/pdf"): bytes})
    def get(self, request: Request, token: str) -> HttpResponse:
        ticket = self.resolve(request, token)
        with tenant_context(ticket.organization):
            response = HttpResponse(services.pdf_bytes(ticket), content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="billet-{ticket.code}.pdf"'
            return _private(response)


class PublicTicketIcsView(PublicTicketMixin):
    @extend_schema(responses={(200, "text/calendar"): str})
    def get(self, request: Request, token: str) -> HttpResponse:
        ticket = self.resolve(request, token)
        with tenant_context(ticket.organization):
            response = HttpResponse(
                services.ics(ticket), content_type="text/calendar; charset=utf-8"
            )
            response["Content-Disposition"] = 'attachment; filename="mariage.ics"'
            return _private(response)


class PublicRsvpView(PublicTicketMixin):
    @extend_schema(request=RsvpSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request: Request, token: str) -> Response:
        serializer = RsvpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = self.resolve(request, token)
        with tenant_context(ticket.organization):
            guest = services.answer_rsvp(ticket, serializer.validated_data["accepted"])
            return Response({"rsvp_status": guest.rsvp_status})
