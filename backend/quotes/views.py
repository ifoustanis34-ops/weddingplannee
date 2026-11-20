from __future__ import annotations

from datetime import datetime, time
from typing import Any

from django.db.models import Count, Exists, OuterRef, QuerySet
from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import generics, serializers, status
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.models import User
from contracts.models import Contract
from core.exceptions import BusinessError
from core.pagination import DefaultCursorPagination
from core.permissions import IsTenantMember
from documents import generation
from documents.rendering import fingerprint
from documents.serializers import GeneratedDocumentSerializer
from organizations.timezones import org_tz

from . import selectors, services
from .filters import QuoteFilter
from .models import Quote
from .permissions import QuotePermission
from .serializers import (
    DuplicateSerializer,
    QuoteListSerializer,
    QuoteSerializer,
    RefuseSerializer,
    SendSerializer,
)

PERMISSIONS = [IsTenantMember, QuotePermission]


def _lines(validated: list[dict[str, Any]]) -> list[services.LineInput]:
    return [
        services.LineInput(
            label=line["label"],
            unit=line.get("unit", "flat"),
            unit_price=line["unit_price"],
            quantity=line["quantity"],
            description=line.get("description", ""),
            service_item=line.get("service_item"),
            icon=line.get("icon", ""),
        )
        for line in validated
    ]


def _quotes() -> QuerySet[Quote]:
    return Quote.objects.select_related("client", "contract").prefetch_related("lines", "partners")


class QuotePagination(DefaultCursorPagination):
    ordering = "-created_at"


class QuoteListView(generics.ListCreateAPIView[Quote]):
    permission_classes = PERMISSIONS
    pagination_class = QuotePagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = QuoteFilter

    def get_serializer_class(self):  # type: ignore[no-untyped-def]
        return QuoteSerializer if self.request.method == "POST" else QuoteListSerializer

    def get_queryset(self) -> QuerySet[Quote]:
        if getattr(self, "swagger_fake_view", False):
            return Quote.all_tenants.none()
        queryset = Quote.objects.select_related("client").annotate(
            has_contract=Exists(Contract.objects.filter(quote=OuterRef("pk")))
        )
        if "is_template" not in self.request.query_params:
            queryset = queryset.filter(is_template=False)
        return selectors.search(queryset, self.request.query_params.get("search", ""))

    @extend_schema(request=QuoteSerializer, responses={201: QuoteSerializer})
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = QuoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        lines = _lines(data.pop("lines", []))
        quote = services.create_quote(data, lines, user=request.user)  # type: ignore[arg-type]
        return Response(QuoteSerializer(_quotes().get(pk=quote.pk)).data, status=201)


class QuoteSummaryView(generics.GenericAPIView[Quote]):
    """Counts per status for the list tabs."""

    permission_classes = PERMISSIONS

    @extend_schema(responses={200: OpenApiResponse(description="{status: count}")})
    def get(self, request: Request) -> Response:
        counts = (
            Quote.objects.filter(is_template=False).values("status").annotate(count=Count("id"))
        )
        summary = dict.fromkeys(Quote.Status.values, 0)
        summary.update({row["status"]: row["count"] for row in counts})
        summary["templates"] = Quote.objects.filter(is_template=True).count()
        return Response(summary)


class QuoteStatsView(generics.GenericAPIView[Quote]):
    """Tiles of the quote list: creation time, sent this month, acceptance, amount pending."""

    permission_classes = PERMISSIONS

    @extend_schema(
        responses=inline_serializer(
            "QuoteStats",
            {
                "median_creation_minutes": serializers.IntegerField(allow_null=True),
                "sent_this_month": serializers.IntegerField(),
                "acceptance_rate": serializers.IntegerField(allow_null=True),
                "pending_amount": serializers.IntegerField(),
            },
        )
    )
    def get(self, request: Request) -> Response:
        now = timezone.now()
        tz = org_tz(request.organization)  # type: ignore[attr-defined]
        local = now.astimezone(tz).date()
        month_start = datetime.combine(local.replace(day=1), time(0), tzinfo=tz)
        return Response(selectors.stats(now, month_start))


class QuoteDetailView(generics.RetrieveUpdateDestroyAPIView[Quote]):
    serializer_class = QuoteSerializer
    permission_classes = PERMISSIONS
    http_method_names = ["get", "patch", "delete"]

    def get_queryset(self) -> QuerySet[Quote]:
        if getattr(self, "swagger_fake_view", False):
            return Quote.all_tenants.none()
        return _quotes()

    def patch(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        quote = self.get_object()
        serializer = QuoteSerializer(quote, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        lines = _lines(data.pop("lines")) if "lines" in data else None
        services.update_quote(quote, data, lines, user=request.user)  # type: ignore[arg-type]
        return Response(QuoteSerializer(_quotes().get(pk=quote.pk)).data)

    def perform_destroy(self, instance: Quote) -> None:
        if instance.status != Quote.Status.DRAFT and not instance.is_template:
            raise BusinessError(
                "quote_not_draft",
                "Seuls les brouillons se suppriment. Un devis envoyé reste tracé.",
            )
        instance.delete()


class QuoteActionView(generics.GenericAPIView[Quote]):
    permission_classes = PERMISSIONS

    def get_queryset(self) -> QuerySet[Quote]:
        if getattr(self, "swagger_fake_view", False):
            return Quote.all_tenants.none()
        return _quotes()

    def respond(self, quote: Quote, code: int = status.HTTP_200_OK) -> Response:
        return Response(QuoteSerializer(_quotes().get(pk=quote.pk)).data, status=code)

    @property
    def user(self) -> User:
        return self.request.user  # type: ignore[return-value]


class SendQuoteView(QuoteActionView):
    """``channel``: ``email`` (default) or ``whatsapp`` (the planner shares the link)."""

    @extend_schema(request=SendSerializer, responses=QuoteSerializer)
    def post(self, request: Request, pk: str) -> Response:
        serializer = SendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quote = services.send_quote(
            self.get_object(), user=self.user, channel=serializer.validated_data["channel"]
        )
        return self.respond(quote)


class AcceptQuoteView(QuoteActionView):
    """The client accepted by phone or in person: the planner records it."""

    @extend_schema(request=None, responses=QuoteSerializer)
    def post(self, request: Request, pk: str) -> Response:
        return self.respond(services.accept_quote(self.get_object(), user=self.user))


class RefuseQuoteView(QuoteActionView):
    @extend_schema(request=RefuseSerializer, responses=QuoteSerializer)
    def post(self, request: Request, pk: str) -> Response:
        serializer = RefuseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quote = services.refuse_quote(
            self.get_object(), user=self.user, reason=serializer.validated_data["reason"]
        )
        return self.respond(quote)


class DuplicateQuoteView(QuoteActionView):
    @extend_schema(request=DuplicateSerializer, responses={201: QuoteSerializer})
    def post(self, request: Request, pk: str) -> Response:
        serializer = DuplicateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        copy = services.duplicate_quote(
            self.get_object(),
            user=self.user,
            as_template=serializer.validated_data["as_template"],
            client=serializer.validated_data.get("client"),
        )
        return self.respond(copy, status.HTTP_201_CREATED)


class ConvertQuoteView(QuoteActionView):
    manage_only = True

    @extend_schema(request=None, responses={201: QuoteSerializer})
    def post(self, request: Request, pk: str) -> Response:
        quote = self.get_object()
        services.convert_to_contract(quote, user=self.user, request=request)
        return self.respond(quote, status.HTTP_201_CREATED)


class QuotePdfView(QuoteActionView):
    """The quote as it is now: the last generated version if nothing changed since, else a
    fresh rendering (not stored: generating a version is « Générer le PDF » or the send)."""

    @extend_schema(responses={(200, "application/pdf"): bytes})
    def get(self, request: Request, pk: str) -> HttpResponse:
        quote = self.get_object()
        snapshot = generation.quote_snapshot(quote)
        document = generation.latest(quote)
        if document is not None and fingerprint(document.data_snapshot) == fingerprint(snapshot):
            content = generation.pdf_bytes(document)
        else:
            content = generation.render(snapshot).pdf
        response = HttpResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{generation.filename(quote)}"'
        return response


class GenerateQuoteView(QuoteActionView):
    """« Générer le PDF »: freezes a version (snapshot, PDF, PNG, SHA-256)."""

    @extend_schema(request=None, responses=GeneratedDocumentSerializer)
    def post(self, request: Request, pk: str) -> Response:
        document = generation.generate(self.get_object())
        return Response(GeneratedDocumentSerializer(document).data, status=status.HTTP_201_CREATED)
