from __future__ import annotations

from django.http import Http404, HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Membership
from core import audit
from core.exceptions import BusinessError
from core.permissions import IsTenantMember, roles_allowed

from . import generation, services
from .serializers import BrandingFileSerializer, BrandingSerializer, PreviewSerializer

# Paramètres › Identité des documents: owner only (docs/specs/devis-billets.md §4).
OWNER_ONLY: list[type[BasePermission]] = [IsTenantMember, roles_allowed(Membership.Role.OWNER)]


class BrandingView(APIView):
    permission_classes = OWNER_ONLY

    @extend_schema(responses=BrandingSerializer)
    def get(self, request: Request) -> Response:
        return Response(BrandingSerializer(services.get_branding()).data)

    @extend_schema(request=BrandingSerializer, responses=BrandingSerializer)
    def patch(self, request: Request) -> Response:
        branding = services.get_branding()
        serializer = BrandingSerializer(branding, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        changes = services.update_branding(branding, dict(serializer.validated_data))
        if changes:
            audit.record("branding.updated", branding, request=request, changes=changes)
        return Response(BrandingSerializer(branding).data)


class BrandingFileView(APIView):
    """Upload (multipart: kind + file) or remove (?kind=) a logo, signature or stamp."""

    permission_classes = OWNER_ONLY

    @extend_schema(request=BrandingFileSerializer, responses=BrandingSerializer)
    def post(self, request: Request) -> Response:
        serializer = BrandingFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kind = serializer.validated_data["kind"]
        branding = services.store_file(
            services.get_branding(), kind, serializer.validated_data["file"].read()
        )
        audit.record("branding.file_uploaded", branding, request=request, changes={"kind": kind})
        return Response(BrandingSerializer(branding).data)

    @extend_schema(responses=BrandingSerializer)
    def delete(self, request: Request) -> Response:
        kind = request.query_params.get("kind", "")
        branding = services.remove_file(services.get_branding(), kind)
        audit.record("branding.file_removed", branding, request=request, changes={"kind": kind})
        return Response(BrandingSerializer(branding).data)


class PreviewView(APIView):
    """The server rendering of a document as a PNG (all pages stacked), cached 10 minutes:
    the editor shows exactly the future PDF (docs/specs/devis-billets.md §3)."""

    permission_classes = [IsTenantMember]

    @extend_schema(request=PreviewSerializer, responses={(200, "image/png"): OpenApiTypes.BINARY})
    def post(self, request: Request) -> HttpResponse:
        from quotes.models import Quote
        from quotes.serializers import QuoteSerializer

        serializer = PreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        base = None
        if params.get("quote"):
            base = Quote.objects.filter(pk=params["quote"]).prefetch_related("partners").first()
            if base is None:
                raise Http404
        data = params["draft"]
        if data:
            draft = QuoteSerializer(data=data, partial=True)
            draft.is_valid(raise_exception=True)
            snapshot = generation.draft_snapshot(dict(draft.validated_data), base)
        elif base is not None:
            snapshot = generation.quote_snapshot(base)
        else:
            raise BusinessError("invalid", "Rien à afficher.", {"draft": ["Données manquantes."]})
        png, pages = generation.preview(snapshot)
        response = HttpResponse(png, content_type="image/png")
        response["X-Page-Count"] = str(pages)
        response["Cache-Control"] = "private, no-store"
        return response


class DesignsView(APIView):
    """Quote designs and colour palettes offered in the editor (R4b moves palettes to the DB)."""

    permission_classes = [IsTenantMember]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request: Request) -> Response:
        from .palettes import PALETTES
        from .quote_document import TEMPLATES

        branding = services.get_branding()
        return Response(
            {
                "designs": [{"code": code, "name": name} for code, name in TEMPLATES.items()],
                "palettes": [
                    {"code": p.code, "name": p.name, "dark": p.dark, "accent": p.accent}
                    for p in PALETTES.values()
                ],
                "default_design": branding.quote_design,
                "default_palette": branding.quote_palette,
                "default_tagline": branding.quote_tagline,
            }
        )
