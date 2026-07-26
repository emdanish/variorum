from __future__ import annotations

import hashlib
import hmac

from app.services.github.webhook import verify_webhook_signature

SECRET = "topsecret"
BODY = b'{"action":"opened"}'


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_valid_signature_accepted():
    assert verify_webhook_signature(SECRET, BODY, _sign(SECRET, BODY)) is True


def test_wrong_secret_rejected():
    assert verify_webhook_signature(SECRET, BODY, _sign("other", BODY)) is False


def test_tampered_body_rejected():
    sig = _sign(SECRET, BODY)
    assert verify_webhook_signature(SECRET, b'{"action":"closed"}', sig) is False


def test_missing_signature_rejected():
    assert verify_webhook_signature(SECRET, BODY, None) is False


def test_missing_secret_rejected():
    assert verify_webhook_signature("", BODY, _sign(SECRET, BODY)) is False


def test_malformed_header_rejected():
    digest = hmac.new(SECRET.encode(), BODY, hashlib.sha256).hexdigest()
    assert verify_webhook_signature(SECRET, BODY, digest) is False  # missing sha256= prefix
