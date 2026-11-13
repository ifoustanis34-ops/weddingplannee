"""Short-lived signed URLs for private files (docs/specs/devis-billets.md §4).

Files are never served from a public /media/ path: the API hands out
``/api/v1/files/<token>`` where the token signs the storage path with a timestamp.
"""

from __future__ import annotations

import mimetypes

from django.core import signing
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, HttpRequest
from django.views.decorators.http import require_GET

SALT = "core.signed-files"
MAX_AGE = 3600  # seconds


def signed_url(name: str | None) -> str | None:
    if not name:
        return None
    return f"/api/v1/files/{signing.dumps(name, salt=SALT, compress=True)}"


@require_GET
def serve(request: HttpRequest, token: str) -> FileResponse:
    try:
        name = signing.loads(token, salt=SALT, max_age=MAX_AGE)
    except signing.BadSignature as exc:  # also covers SignatureExpired
        raise Http404 from exc
    if not isinstance(name, str) or ".." in name or not default_storage.exists(name):
        raise Http404
    content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
    response = FileResponse(default_storage.open(name, "rb"), content_type=content_type)
    response["Cache-Control"] = "private, max-age=600"
    response["X-Content-Type-Options"] = "nosniff"
    if content_type == "image/svg+xml":
        # A cleaned SVG is still served with a sandboxing policy (no script, no network).
        response["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'"
    return response
