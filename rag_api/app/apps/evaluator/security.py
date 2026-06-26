# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import hmac
from typing import Optional
from urllib.parse import urlparse

from django.conf import settings
from rest_framework.permissions import BasePermission


def _normalize_host(entry: Optional[str]) -> Optional[str]:
    """Reduce an allowlist entry (bare host, host:port, or full URL) to its host.
    Returns the lowercased, port-stripped host, or None if blank/unparseable.
    """

    entry = (entry or "").strip()
    if not entry:
        return None
    try:
        # Prefix '//' so urlparse reads a bare 'host'/'host:port' as a netloc.
        return urlparse(entry if "://" in entry else f"//{entry}").hostname
    except ValueError:
        return None


def is_allowed_callback_url(url: Optional[str]) -> bool:
    """True when `url` is an http(s) URL whose host is exactly allowlisted.
    Exact host match (case-insensitive, port ignored) blocks substring, non-http
    scheme, and path tricks — stops the worker POSTing the secret elsewhere (SSRF).
    """

    if not url:
        return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    allowed = {host for host in (_normalize_host(e) for e in settings.ALLOWED_CALLBACK_HOSTS) if host}
    return parsed.hostname.lower() in allowed


class HasInternalSecret(BasePermission):
    """Reject any caller lacking the shared `X-Internal-Secret` header (403).
    Guards every rag_api endpoint; compared constant-time to resist timing attacks.
    """

    message = "Missing or invalid internal secret."

    def has_permission(self, request, view) -> bool:
        provided = request.headers.get("X-Internal-Secret") or ""
        expected = getattr(settings, "RAG_INBOUND_SECRET", "") or ""
        if not provided or not expected:
            return False
        return hmac.compare_digest(provided, expected)
