from __future__ import annotations

import httpx

from app.ai.base import (
    ProviderAuthError,
    ProviderBadRequestError,
    ProviderError,
    ProviderQuotaError,
    ProviderTransientError,
)

DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


def classify_http_error(provider: str, response: httpx.Response) -> ProviderError:
    status = response.status_code
    body = response.text[:500]
    if status in (401, 403):
        return ProviderAuthError(provider, f"auth failed: {body}", status_code=status)
    if status == 429:
        return ProviderQuotaError(provider, f"rate limited / quota: {body}", status_code=status)
    if status == 400:
        return ProviderBadRequestError(provider, f"bad request: {body}", status_code=status)
    if 500 <= status < 600:
        return ProviderTransientError(provider, f"server error: {body}", status_code=status)
    return ProviderError(provider, f"unexpected status {status}: {body}", status_code=status)


def wrap_transport_error(provider: str, exc: httpx.HTTPError) -> ProviderTransientError:
    return ProviderTransientError(provider, f"transport error: {exc}")


def strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1] if "\n" in stripped else stripped[3:]
        if stripped.endswith("```"):
            stripped = stripped[: -3]
    return stripped.strip()
