"""Signed ticket tokens (docs/specs/devis-billets.md §7).

token = base64url(16 random bytes ‖ HMAC-SHA256(key, id)[:10]); the key of each organization
is derived with HKDF-SHA256 from DOCUMENTS_MASTER_KEY, salted with the organization's id.
No key is written in the code; the token alone tells nothing (random id) and cannot be forged
without the master key. Only the SHA-256 of a token is stored and sent to offline scanners.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass

from django.conf import settings

ID_BYTES = 16
MAC_BYTES = 10
INFO = b"wedivo:tickets:v1"
# Dev and tests only: production refuses to start without DOCUMENTS_MASTER_KEY (settings/prod).
DEV_MASTER_KEY = "wedivo-dev-only-documents-master-key"


def _hkdf(master: bytes, salt: bytes, info: bytes, length: int = 32) -> bytes:
    """HKDF-SHA256 (RFC 5869): extract then expand."""
    prk = hmac.new(salt, master, hashlib.sha256).digest()
    output, block, counter = b"", b"", 1
    while len(output) < length:
        block = hmac.new(prk, block + info + bytes([counter]), hashlib.sha256).digest()
        output += block
        counter += 1
    return output[:length]


def organization_key(organization_id: uuid.UUID) -> bytes:
    master = (settings.DOCUMENTS_MASTER_KEY or DEV_MASTER_KEY).encode()
    return _hkdf(master, organization_id.bytes, INFO)


def _mac(organization_id: uuid.UUID, ticket_id: bytes) -> bytes:
    return hmac.new(organization_key(organization_id), ticket_id, hashlib.sha256).digest()[
        :MAC_BYTES
    ]


def _encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


@dataclass(frozen=True)
class Parsed:
    ticket_id: bytes
    mac: bytes

    @property
    def ticket_id_hex(self) -> str:
        return self.ticket_id.hex()


def new_token(organization_id: uuid.UUID) -> tuple[str, str]:
    """A fresh token and its id (hex, stored to find the ticket and re-render its QR)."""
    ticket_id = secrets.token_bytes(ID_BYTES)
    return token_for(organization_id, ticket_id.hex()), ticket_id.hex()


def token_for(organization_id: uuid.UUID, ticket_id_hex: str) -> str:
    ticket_id = bytes.fromhex(ticket_id_hex)
    return _encode(ticket_id + _mac(organization_id, ticket_id))


def parse(token: str) -> Parsed | None:
    """Shape only (no key needed): the id to look the ticket up, and the signature to check."""
    try:
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
    except (binascii.Error, ValueError):
        return None
    if len(raw) != ID_BYTES + MAC_BYTES:
        return None
    # Canonical form only: the unused bits of the last character must be zero, so one ticket
    # never has two spellings (``…A`` and ``…B`` would otherwise decode to the same bytes).
    if _encode(raw) != token:
        return None
    return Parsed(raw[:ID_BYTES], raw[ID_BYTES:])


def verify(organization_id: uuid.UUID, parsed: Parsed) -> bool:
    return hmac.compare_digest(_mac(organization_id, parsed.ticket_id), parsed.mac)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
