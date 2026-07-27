from __future__ import annotations

from app.ai.base import (
    AIProvider,
    AllProvidersFailedError,
    CompletionResult,
    Message,
    ProviderBadRequestError,
    ProviderError,
)
from app.ai.providers._common import parse_json_object
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
                # In JSON mode, a 200 response that isn't valid JSON is a failed
                # answer — treat it as a provider failure so the next provider
                # gets a chance, instead of surfacing a parse error to the caller.
                if json_mode:
                    parse_json_object(result.text)
                logger.info(
                    "ai call ok provider=%s model=%s purpose=%s latency_ms=%s",
                    provider.name,
                    provider.model,
                    purpose,
                    result.latency_ms,
                )
                return result
            except ValueError as exc:
                logger.warning(
                    "ai provider returned unparseable JSON provider=%s purpose=%s falling back: %s",
                    provider.name,
                    purpose,
                    exc,
                )
                errors.append(ProviderBadRequestError(provider.name, f"unparseable JSON: {exc}"))
            except ProviderError as exc:
                logger.warning(
                    "ai provider failed provider=%s kind=%s purpose=%s falling back: %s",
                    provider.name,
                    exc.kind.value,
                    purpose,
                    exc,
                )
                errors.append(exc)

        # A single, greppable signal for "AI is fully down" — every configured
        # provider failed (or none is configured). Alert on this.
        logger.error(
            "ai all providers failed purpose=%s tried=%d", purpose, len(errors)
        )
        raise AllProvidersFailedError(errors)
