from __future__ import annotations

from app.ai.base import (
    AIProvider,
    AllProvidersFailedError,
    CompletionResult,
    Message,
    ProviderError,
)
from app.core.logging import get_logger

logger = get_logger("variorum.ai")


class ProviderManager:
    """Holds an ordered list of providers and tries them in turn. Unconfigured
    providers are skipped; a provider that raises is logged and the next one is
    tried. Callers never choose a provider — that is the whole point."""

    def __init__(self, providers: list[AIProvider]) -> None:
        self._providers = providers

    @property
    def active_providers(self) -> list[AIProvider]:
        return [p for p in self._providers if p.is_configured]

    @property
    def has_active_provider(self) -> bool:
        return bool(self.active_providers)

    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        json_mode: bool = False,
        purpose: str = "generic",
    ) -> CompletionResult:
        errors: list[ProviderError] = []
        for provider in self._providers:
            if not provider.is_configured:
                continue
            try:
                result = await provider.complete(
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                )
                logger.info(
                    "ai call ok provider=%s model=%s purpose=%s latency_ms=%s",
                    provider.name,
                    provider.model,
                    purpose,
                    result.latency_ms,
                )
                return result
            except ProviderError as exc:
                logger.warning(
                    "ai provider failed provider=%s kind=%s purpose=%s falling back: %s",
                    provider.name,
                    exc.kind.value,
                    purpose,
                    exc,
                )
                errors.append(exc)

        raise AllProvidersFailedError(errors)
