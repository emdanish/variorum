from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.ai.base import (
    ProviderAuthError,
    ProviderBadRequestError,
    ProviderError,
    ProviderQuotaError,
    ProviderTransientError,
)

DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=10.0)

# Bracketed numeric citation markers a web-augmented model (e.g. Perplexity)
# tends to inject into prose — "…off the request path [1]." We answer only from
# supplied context, so these markers are noise; strip them from user-facing prose.
_CITATION_MARKER = re.compile(r"\s*\[\d+(?:\s*[,–-]\s*\d+)*\]")


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


def clean_prose(text: str) -> str:
    """Tidy a model's free-form prose for display: drop injected citation markers
    like ``[1]`` / ``[1, 2]`` and any wrapping code fence, and trim whitespace.
    Keeps content intact; only removes formatting artifacts."""
    s = unwrap_sole_code_fence(text).strip()
    s = _CITATION_MARKER.sub("", s)
    return s.strip()


def unwrap_sole_code_fence(text: str) -> str:
    """Remove a wrapping code fence from generated FILE content, but only when
    the whole output is a single fenced block (the model ignored "no fences").
    If the content contains multiple fences — e.g. a Markdown doc with real code
    examples — it is left untouched, so legitimate fences are never corrupted."""
    stripped = text.strip()
    if not stripped.startswith("```") or stripped.count("```") != 2 or not stripped.endswith("```"):
        return text
    body = stripped.split("\n", 1)[1] if "\n" in stripped else ""
    if body.endswith("```"):
        body = body[:-3]
    return body.strip("\n")


def _first_json_object(text: str) -> str | None:
    """Return the first balanced ``{...}`` object embedded in text, or None.
    Handles a model that wraps its JSON in prose or citations."""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse a model's response into a JSON object, tolerantly.

    Strips code fences, then falls back to extracting the first balanced object
    if the model wrapped its JSON in prose. Raises ``ValueError`` if no JSON
    object can be recovered — which callers treat as a provider failure so the
    fallback chain moves on to the next provider."""
    stripped = strip_json_fence(text)
    try:
        obj = json.loads(stripped)
    except (ValueError, TypeError):
        extracted = _first_json_object(stripped)
        if extracted is None:
            raise ValueError("no JSON object found in model output") from None
        obj = json.loads(extracted)  # propagates ValueError on genuinely bad JSON
    if not isinstance(obj, dict):
        raise ValueError("model output was not a JSON object")
    return obj
