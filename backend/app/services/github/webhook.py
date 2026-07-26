from __future__ import annotations

import hashlib
import hmac


def verify_webhook_signature(secret: str, payload: bytes, signature_header: str | None) -> bool:
    """Verify a GitHub webhook using the `X-Hub-Signature-256` header.

    GitHub sends `sha256=<hex hmac>`. We recompute the HMAC over the raw body
    and compare in constant time. Returns False on any missing/malformed input
    rather than raising, so callers can respond with 401 uniformly."""
    if not secret or not signature_header:
        return False
    if not signature_header.startswith("sha256="):
        return False
    expected = signature_header.removeprefix("sha256=")
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, expected)
