from __future__ import annotations

from app.core.config import (
    DEFAULT_DATABASE_URL,
    DEFAULT_SESSION_SECRET,
    Settings,
)
from app.core.ratelimit import RateLimiter, classify
from tests.conftest import requires_db


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "environment": "production",
        "session_secret": "a-strong-random-secret-value-1234567890",
        "github_webhook_secret": "whsec",
        "database_url": "postgresql+psycopg://user:pw@db.example.com/prod",
        "cors_origins": ["https://app.example.com"],
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)  # type: ignore[arg-type]


def test_production_config_clean_has_no_issues():
    assert _settings().production_security_issues() == []


def test_production_config_flags_default_session_secret():
    issues = _settings(session_secret=DEFAULT_SESSION_SECRET).production_security_issues()
    assert any("SESSION_SECRET" in i for i in issues)


def test_production_config_flags_missing_webhook_secret():
    issues = _settings(github_webhook_secret="").production_security_issues()
    assert any("GITHUB_WEBHOOK_SECRET" in i for i in issues)


def test_production_config_flags_default_database_url():
    issues = _settings(database_url=DEFAULT_DATABASE_URL).production_security_issues()
    assert any("DATABASE_URL" in i for i in issues)


def test_production_config_flags_wildcard_cors():
    issues = _settings(cors_origins=["*"]).production_security_issues()
    assert any("CORS_ORIGINS" in i for i in issues)


def test_ratelimit_classify_buckets():
    assert classify("/api/v1/auth/github/login") == "auth"
    assert classify("/webhooks/github") == "webhook"
    assert classify("/api/v1/repositories/1/ask") == "ai"
    assert classify("/api/v1/findings/1/open-pr") == "ai"
    assert classify("/api/v1/risk-findings/1/generate-tests") == "ai"
    assert classify("/api/v1/repositories") is None


def test_ratelimit_blocks_after_limit():
    limiter = RateLimiter()
    # auth bucket is 20/60s; the 21st request in the same window is denied.
    now = 1000.0
    allowed = [limiter.allow("auth", "1.2.3.4", now) for _ in range(20)]
    assert all(allowed)
    assert limiter.allow("auth", "1.2.3.4", now) is False
    # a different client is unaffected
    assert limiter.allow("auth", "5.6.7.8", now) is True
    # after the window elapses the original client is allowed again
    assert limiter.allow("auth", "1.2.3.4", now + 61) is True


@requires_db
def test_security_headers_present(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "no-referrer"
