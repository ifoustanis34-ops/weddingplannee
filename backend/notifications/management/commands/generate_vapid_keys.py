"""Print a VAPID key pair for `.env` (Web Push). Run once per environment, keep it secret."""

from __future__ import annotations

import base64
from typing import Any

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Génère les clés VAPID des notifications push (à mettre dans .env)."

    def handle(self, *args: Any, **options: Any) -> None:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec

        key = ec.generate_private_key(ec.SECP256R1())
        private = key.private_numbers().private_value.to_bytes(32, "big")
        public = key.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )

        def b64(raw: bytes) -> str:
            return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

        self.stdout.write(f"VAPID_PUBLIC_KEY={b64(public)}")
        self.stdout.write(f"VAPID_PRIVATE_KEY={b64(private)}")
