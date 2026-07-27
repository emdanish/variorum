from __future__ import annotations

from app.core.ratelimit import RateLimiter, classify


def test_classify_buckets():
    assert classify("/api/v1/auth/github/login") == "auth"
    assert classify("/api/v1/auth/github/callback") == "auth"
    assert classify("/webhooks/github") == "webhook"
    # original AI endpoints
    assert classify("/api/v1/repositories/1/ask") == "ai"
    assert classify("/api/v1/findings/5/open-pr") == "ai"
    assert classify("/api/v1/risk-findings/5/generate-tests") == "ai"
    # broadened AI coverage
    for path in (
        "/api/v1/repositories/1/orientation",
        "/api/v1/repositories/1/decisions",
        "/api/v1/repositories/1/change-briefing",
        "/api/v1/repositories/1/analyze-pr",
        "/api/v1/repositories/1/contradictions/7",
        "/api/v1/repositories/1/pr-briefing/7",
        "/api/v1/repositories/1/pr-comment/7",
    ):
        assert classify(path) == "ai", path
    # unclassified paths are unlimited
    assert classify("/api/v1/repositories") is None
    assert classify("/api/v1/system/status") is None


def test_rate_limiter_blocks_past_limit_and_resets_after_window():
    limiter = RateLimiter()
    # "ai" bucket is (30, 60s); drive a small synthetic bucket via monotonic clock.
    now = 1000.0
    allowed = sum(1 for _ in range(30) if limiter.allow("ai", "1.2.3.4", now))
    assert allowed == 30  # first 30 within the window pass
    assert limiter.allow("ai", "1.2.3.4", now) is False  # 31st is blocked

    # a different client has its own bucket
    assert limiter.allow("ai", "9.9.9.9", now) is True

    # after the window elapses, the original client is allowed again
    assert limiter.allow("ai", "1.2.3.4", now + 61.0) is True


def test_rate_limiter_auth_bucket_independent_of_ai():
    limiter = RateLimiter()
    now = 500.0
    # exhausting one bucket doesn't affect another for the same client
    for _ in range(20):
        limiter.allow("auth", "1.1.1.1", now)
    assert limiter.allow("auth", "1.1.1.1", now) is False
    assert limiter.allow("ai", "1.1.1.1", now) is True
