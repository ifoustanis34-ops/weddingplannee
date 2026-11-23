from __future__ import annotations

import contextlib
from typing import Any

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core import antibot, audit
from core.audit import client_ip
from core.exceptions import BusinessError
from core.tenant import tenant_context
from organizations import services as organization_services

from . import services, tokens
from .models import User
from .serializers import (
    AcceptInvitationSerializer,
    InvitationPreviewSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileSerializer,
    SessionSerializer,
    SignupSerializer,
    SlugAvailabilitySerializer,
    SlugQuerySerializer,
    TokenSerializer,
)


def session_payload(user: User) -> dict[str, Any]:
    return dict(
        SessionSerializer({"user": user, "organizations": services.active_memberships(user)}).data
    )


class PublicAPIView(APIView):
    authentication_classes: list[type] = []
    permission_classes = [AllowAny]


@method_decorator(ensure_csrf_cookie, name="get")
class CsrfView(PublicAPIView):
    """Sets the ``csrftoken`` cookie the SPA sends back in ``X-CSRFToken``."""

    @extend_schema(responses={204: None})
    def get(self, request: Request) -> Response:
        return Response(status=status.HTTP_204_NO_CONTENT)


class FormTokenView(PublicAPIView):
    """Dated, signed token the public forms send back (anti-bot, core/antibot.py)."""

    @extend_schema(
        responses=inline_serializer("FormToken", {"form_token": serializers.CharField()})
    )
    def get(self, request: Request) -> Response:
        response = Response({"form_token": antibot.issue()})
        response["Cache-Control"] = "no-store"
        return response


class SignupView(PublicAPIView):
    @extend_schema(request=SignupSerializer, responses={201: SessionSerializer})
    def post(self, request: Request) -> Response:
        antibot.check(request.data, min_seconds=settings.ANTIBOT_MIN_SECONDS)
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, _ = services.signup(
            services.SignupData(**serializer.validated_data), ip=client_ip(request)
        )
        response = Response(session_payload(user), status=status.HTTP_201_CREATED)
        tokens.set_auth_cookies(response, tokens.issue_tokens(user))
        return response


class LoginView(PublicAPIView):
    @extend_schema(request=LoginSerializer, responses={200: SessionSerializer})
    def post(self, request: Request) -> Response:
        antibot.check(request.data)
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.login(**serializer.validated_data, ip=client_ip(request))
        response = Response(session_payload(user))
        tokens.set_auth_cookies(response, tokens.issue_tokens(user))
        return response


class RefreshView(PublicAPIView):
    @extend_schema(request=None, responses={204: None})
    def post(self, request: Request) -> Response:
        _, refresh = tokens.rotate(request.COOKIES.get(settings.JWT_REFRESH_COOKIE))
        response = Response(status=status.HTTP_204_NO_CONTENT)
        tokens.set_auth_cookies(response, refresh)
        return response


class LogoutView(PublicAPIView):
    @extend_schema(request=None, responses={204: None})
    def post(self, request: Request) -> Response:
        raw = request.COOKIES.get(settings.JWT_REFRESH_COOKIE)
        if raw:
            # An invalid or expired token is already unusable: nothing to revoke.
            with contextlib.suppress(BusinessError):
                tokens.revoke(tokens.parse_refresh(raw))
        response = Response(status=status.HTTP_204_NO_CONTENT)
        tokens.clear_auth_cookies(response)
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=SessionSerializer)
    def get(self, request: Request) -> Response:
        return Response(session_payload(request.user))  # type: ignore[arg-type]

    @extend_schema(request=ProfileSerializer, responses=SessionSerializer)
    def patch(self, request: Request) -> Response:
        """« Mon profil »: the person changes their own name and phone."""
        serializer = ProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.update_profile(
            request.user,  # type: ignore[arg-type]
            full_name=serializer.validated_data.get("full_name"),
            phone=serializer.validated_data.get("phone"),
        )
        return Response(session_payload(request.user))  # type: ignore[arg-type]


class MePasswordView(APIView):
    """Change one's own password (the current one is asked first)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=PasswordChangeSerializer, responses={204: None})
    def post(self, request: Request) -> Response:
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.change_password(
            request.user,  # type: ignore[arg-type]
            current=serializer.validated_data["current_password"],
            new=serializer.validated_data["new_password"],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeTourView(APIView):
    """The guided tour was followed or declined: it is no longer offered at sign-in."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def post(self, request: Request) -> Response:
        services.finish_tour(request.user)  # type: ignore[arg-type]
        return Response(status=status.HTTP_204_NO_CONTENT)


class SlugAvailableView(PublicAPIView):
    """``?slug=`` checks a slug; ``?name=`` proposes an available slug from the company name."""

    @extend_schema(parameters=[SlugQuerySerializer], responses=SlugAvailabilitySerializer)
    def get(self, request: Request) -> Response:
        query = SlugQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        slug = query.validated_data.get("slug") or ""
        name = query.validated_data.get("name") or ""
        if not slug and name:
            slug = organization_services.suggest_slug(name)
        check = organization_services.check_slug(slug)
        return Response({"slug": check.slug, "available": check.available, "reason": check.reason})


class VerifyEmailView(PublicAPIView):
    @extend_schema(request=TokenSerializer, responses={204: None})
    def post(self, request: Request) -> Response:
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.verify_email(serializer.validated_data["token"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResendVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def post(self, request: Request) -> Response:
        services.request_email_verification(request.user)  # type: ignore[arg-type]
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetView(PublicAPIView):
    @extend_schema(
        request=PasswordResetRequestSerializer,
        responses={204: OpenApiResponse(description="Toujours 204, que l’email existe ou non.")},
    )
    def post(self, request: Request) -> Response:
        antibot.check(request.data, min_seconds=1)
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.request_password_reset(serializer.validated_data["email"], ip=client_ip(request))
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetConfirmView(PublicAPIView):
    @extend_schema(request=PasswordResetConfirmSerializer, responses={204: None})
    def post(self, request: Request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.confirm_password_reset(**serializer.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)


class InvitationView(PublicAPIView):
    """What the emailed link shows before accepting: the space, the role, the address."""

    @extend_schema(responses=InvitationPreviewSerializer)
    def get(self, request: Request, token: str) -> Response:
        invitation = services.invitation_for_token(token)
        return Response(
            InvitationPreviewSerializer(
                {
                    "organization_name": invitation.organization.name,
                    "organization_slug": invitation.organization.slug,
                    "email": invitation.email,
                    "role_label": invitation.get_role_display(),
                    "invited_by_name": (
                        invitation.invited_by.full_name if invitation.invited_by else None
                    ),
                    "has_account": User.objects.filter(email__iexact=invitation.email).exists(),
                }
            ).data
        )


class AcceptInvitationView(PublicAPIView):
    """Join the space and open the session (same cookies as the login)."""

    @extend_schema(request=AcceptInvitationSerializer, responses={200: SessionSerializer})
    def post(self, request: Request, token: str) -> Response:
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, invitation = services.accept_invitation(
            token, **serializer.validated_data, ip=client_ip(request)
        )
        with tenant_context(invitation.organization):
            audit.record(
                "membership.joined",
                invitation,
                changes={"email": invitation.email, "role": invitation.role},
            )
        response = Response(session_payload(user))
        tokens.set_auth_cookies(response, tokens.issue_tokens(user))
        return response
