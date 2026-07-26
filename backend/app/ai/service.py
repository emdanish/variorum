from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from app.ai.base import CompletionResult, Message
from app.ai.manager import ProviderManager
from app.ai.providers._common import strip_json_fence
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.openai_compatible import DeepSeekProvider, PerplexityProvider
from app.core.config import Settings, get_settings


class AIService:
    """High-level facade the rest of the application uses. It knows nothing about
    which provider ultimately answers."""

    def __init__(self, manager: ProviderManager) -> None:
        self._manager = manager

    @property
    def available(self) -> bool:
        return self._manager.has_active_provider

    @property
    def active_provider_names(self) -> list[str]:
        return [p.name for p in self._manager.active_providers]

    async def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        purpose: str = "generic",
    ) -> CompletionResult:
        messages: list[Message] = []
        if system:
            messages.append(Message(role="system", content=system))
        messages.append(Message(role="user", content=prompt))
        return await self._manager.complete(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            purpose=purpose,
        )

    async def complete_json(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        purpose: str = "generic_json",
    ) -> dict[str, Any]:
        messages: list[Message] = []
        if system:
            messages.append(Message(role="system", content=system))
        messages.append(Message(role="user", content=prompt))
        result = await self._manager.complete(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=True,
            purpose=purpose,
        )
        return json.loads(strip_json_fence(result.text))


def build_provider_manager(settings: Settings) -> ProviderManager:
    """Wire providers in the required fallback order:
    Gemini key 1 -> Gemini key 2 -> DeepSeek -> Perplexity."""
    return ProviderManager(
        [
            GeminiProvider(
                name="gemini-1", api_key=settings.gemini_api_key_1, model=settings.gemini_model
            ),
            GeminiProvider(
                name="gemini-2", api_key=settings.gemini_api_key_2, model=settings.gemini_model
            ),
            DeepSeekProvider(
                api_key=settings.deepseek_api_key, model=settings.deepseek_model
            ),
            PerplexityProvider(
                api_key=settings.perplexity_api_key, model=settings.perplexity_model
            ),
        ]
    )


@lru_cache
def get_ai_service() -> AIService:
    return AIService(build_provider_manager(get_settings()))
