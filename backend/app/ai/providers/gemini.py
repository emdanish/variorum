from __future__ import annotations

import time

import httpx

from app.ai.base import AIProvider, CompletionResult, Message, ProviderError
from app.ai.providers._common import (
    DEFAULT_TIMEOUT,
    classify_http_error,
    wrap_transport_error,
)

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(AIProvider):
    """Google Gemini via the Generative Language REST API. Each API key becomes
    its own provider instance so the manager can fall back key-to-key."""

    def __init__(self, *, name: str, api_key: str, model: str) -> None:
        self.name = name
        self._api_key = api_key
        self.model = model

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> CompletionResult:
        system_parts = [m.content for m in messages if m.role == "system"]
        contents = [
            {
                "role": "model" if m.role == "assistant" else "user",
                "parts": [{"text": m.content}],
            }
            for m in messages
            if m.role != "system"
        ]

        generation_config: dict = {"temperature": temperature}
        if max_tokens is not None:
            generation_config["maxOutputTokens"] = max_tokens
        if json_mode:
            generation_config["responseMimeType"] = "application/json"

        payload: dict = {"contents": contents, "generationConfig": generation_config}
        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}

        url = f"{BASE_URL}/models/{self.model}:generateContent"
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        # Send the key in a header, never the URL query string, so
                        # it can't leak into logs via request URLs on errors.
                        "x-goog-api-key": self._api_key,
                    },
                )
        except httpx.HTTPError as exc:
            raise wrap_transport_error(self.name, exc) from exc

        if response.status_code >= 400:
            raise classify_http_error(self.name, response)

        data = response.json()
        text = _extract_text(data)
        if text is None:
            raise ProviderError(self.name, f"no text in response: {data}")

        latency_ms = int((time.perf_counter() - started) * 1000)
        return CompletionResult(
            text=text,
            provider=self.name,
            model=self.model,
            latency_ms=latency_ms,
            raw=data,
        )


def _extract_text(data: dict) -> str | None:
    candidates = data.get("candidates") or []
    if not candidates:
        return None
    parts = (candidates[0].get("content") or {}).get("parts") or []
    texts = [p.get("text", "") for p in parts if "text" in p]
    if not texts:
        return None
    return "".join(texts)
