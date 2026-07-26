from __future__ import annotations

import time

import httpx

from app.ai.base import AIProvider, CompletionResult, Message, ProviderError
from app.ai.providers._common import (
    DEFAULT_TIMEOUT,
    classify_http_error,
    wrap_transport_error,
)


class OpenAICompatibleProvider(AIProvider):
    """Provider for vendors exposing the OpenAI `/chat/completions` shape
    (DeepSeek, Perplexity). Subclasses only set name, base_url, and defaults."""

    base_url: str

    def __init__(self, *, name: str, base_url: str, api_key: str, model: str) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
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
        payload: dict = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers
                )
        except httpx.HTTPError as exc:
            raise wrap_transport_error(self.name, exc) from exc

        if response.status_code >= 400:
            raise classify_http_error(self.name, response)

        data = response.json()
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(self.name, f"unexpected response shape: {data}") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        return CompletionResult(
            text=text or "",
            provider=self.name,
            model=self.model,
            latency_ms=latency_ms,
            raw=data,
        )


class DeepSeekProvider(OpenAICompatibleProvider):
    def __init__(self, *, api_key: str, model: str) -> None:
        super().__init__(
            name="deepseek",
            base_url="https://api.deepseek.com",
            api_key=api_key,
            model=model,
        )


class PerplexityProvider(OpenAICompatibleProvider):
    def __init__(self, *, api_key: str, model: str) -> None:
        super().__init__(
            name="perplexity",
            base_url="https://api.perplexity.ai",
            api_key=api_key,
            model=model,
        )
