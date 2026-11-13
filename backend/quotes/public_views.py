"""Public quote page (no account): view, accept, refuse, download (CLAUDE.md §7.3)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from django.http import Http404, HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core import ratelimit
from core.audit import client_ip
from core.tenant import bypass_tenant, tenant_context
from documents import generation

from . import services
from .models import Quote
from .serializers import PublicQuoteSerializer, RefuseSerializer

PUBLIC_LIMIT, PUBLIC_WINDOW = 60, 60


@contextmanager
def public_quote(request: Request, token: str) -> Iterator[Quote]:
    """Resolve the token across organizations, then work inside the quote's organization."""
    ratelimit.hit(
        "public-quote", client_ip(request) or "unknown", limit=PUBLIC_LIMIT, window=PUBLIC_WINDOW
    )
    with bypass_tenant():
        quote = (
            Quote.all_tenants.select_related("organization")
            .filter(public_token=token, is_template=False, organization__is_active=True)
            .first()
        )
    if quote is None or quote.status == Quote.Status.DRAFT:
        raise Http404
    with tenant_context(quote.organization):
        yield Quote.objects.select_related("client", "organization").get(pk=quote.pk)


class PublicAPIView(APIView):
    authentication_classes: list[type] = []
    permission_classes = [AllowAny]


class PublicQuoteView(PublicAPIView):
    @extend_schema(responses=PublicQuoteSerializer)
    def get(self, request: Request, token: str) -> Response:
        with public_quote(request, token) as quote:
            return Response(PublicQuoteSerializer(quote).data)


class PublicAcceptView(PublicAPIView):
    @extend_schema(request=None, responses=PublicQuoteSerializer)
    def post(self, request: Request, token: str) -> Response:
        with public_quote(request, token) as quote:
            services.accept_quote(quote, user=None, online=True)
            return Response(PublicQuoteSerializer(quote).data)


class PublicRefuseView(PublicAPIView):
    @extend_schema(request=RefuseSerializer, responses=PublicQuoteSerializer)
    def post(self, request: Request, token: str) -> Response:
        serializer = RefuseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with public_quote(request, token) as quote:
            services.refuse_quote(
                quote, user=None, reason=serializer.validated_data["reason"], online=True
            )
            return Response(PublicQuoteSerializer(quote).data)


class PublicPdfView(PublicAPIView):
    @extend_schema(responses={(200, "application/pdf"): bytes})
    def get(self, request: Request, token: str) -> HttpResponse:
        with public_quote(request, token) as quote:
            # The version the client received; a quote never sent is rendered as it is.
            document = generation.latest(quote)
            if document is not None:
                content = generation.pdf_bytes(document)
            else:
                content = generation.render(generation.quote_snapshot(quote)).pdf
            response = HttpResponse(content, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{generation.filename(quote)}"'
            private(response)
            return response


def private(response: HttpResponse) -> HttpResponse:
    """Public documents are not for search engines nor for other sites (§11)."""
    response["X-Robots-Tag"] = "noindex, nofollow"
    response["Referrer-Policy"] = "no-referrer"
    response["Cache-Control"] = "private, max-age=300"
    return response


class PublicPreviewView(PublicAPIView):
    """The document the client received, as an image (all pages)."""

    @extend_schema(responses={(200, "image/png"): bytes})
    def get(self, request: Request, token: str) -> HttpResponse:
        with public_quote(request, token) as quote:
            document = generation.latest(quote)
            if document is not None:
                png, pages = generation.document_preview(document)
            else:
                png, pages = generation.preview(generation.quote_snapshot(quote))
            response = HttpResponse(png, content_type="image/png")
            response["X-Page-Count"] = str(pages)
            return private(response)
