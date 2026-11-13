"""Web Push API: the public key, this device's subscription, a test message."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exceptions import BusinessError

from . import push
from .models import PushSubscription
from .tasks import deliver


class KeysSerializer(serializers.Serializer[Any]):
    p256dh = serializers.CharField(max_length=255)
    auth = serializers.CharField(max_length=64)


class SubscriptionSerializer(serializers.Serializer[Any]):
    endpoint = serializers.URLField(max_length=1000)
    keys = KeysSerializer()


class EndpointSerializer(serializers.Serializer[Any]):
    endpoint = serializers.URLField(max_length=1000)


class PushConfigView(APIView):
    """`enabled` false without VAPID keys: the app then hides the notifications switch."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response({"enabled": push.enabled(), "public_key": settings.VAPID_PUBLIC_KEY})


class SubscriptionView(APIView):
    """Register this device for the signed-in user (a device that changed account follows)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=SubscriptionSerializer, responses={201: None})
    def post(self, request: Request) -> Response:
        serializer = SubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        PushSubscription.objects.update_or_create(
            endpoint=data["endpoint"],
            defaults={
                "user": request.user,
                "p256dh": data["keys"]["p256dh"],
                "auth": data["keys"]["auth"],
                "user_agent": request.headers.get("User-Agent", "")[:255],
            },
        )
        return Response(status=status.HTTP_201_CREATED)


class SubscriptionRemoveView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=EndpointSerializer, responses={204: None})
    def post(self, request: Request) -> Response:
        serializer = EndpointSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PushSubscription.objects.filter(
            user=request.user,  # type: ignore[misc]
            endpoint=serializer.validated_data["endpoint"],
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PushTestView(APIView):
    """« Envoyer une notification de test » to every device of the signed-in user."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        if not push.enabled():
            raise BusinessError("push_disabled", "Les notifications ne sont pas configurées.")
        sent = deliver(
            [str(request.user.pk)],
            {
                "title": "Wedivo",
                "body": "Les notifications fonctionnent sur cet appareil.",
                "url": "/profil",
                "kind": "test",
                "tag": "test",
            },
        )
        if not sent:
            raise BusinessError(
                "no_device", "Aucun appareil n’a reçu la notification : réactivez-les ici."
            )
        return Response({"sent": sent})
