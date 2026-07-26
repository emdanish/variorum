from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.base import CompletionResult, Message
from app.ai.manager import ProviderManager
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.openai_compatible import DeepSeekProvider, PerplexityProvider
from app.ai.service import AIService, build_provider_manager


def test_provider_manager_receives_providers_in_exact_order():
    perplexity = PerplexityProvider(api_key="pp-key", model="sonar")
    deepseek = DeepSeekProvider(api_key="ds-key", model="deepseek-chat")
    gemini_1 = GeminiProvider(name="gemini-1", api_key="g1-key", model="gemini-1.5-flash")
    gemini_2 = GeminiProvider(name="gemini-2", api_key="g2-key", model="gemini-1.5-flash")

    providers = [perplexity, deepseek, gemini_1, gemini_2]
    manager = ProviderManager(providers)

    assert manager._providers == providers
    assert [p.name for p in manager._providers] == [
        "perplexity",
        "deepseek",
        "gemini-1",
        "gemini-2",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        Exception("API Error: 500 Internal Server Error"),
        Exception("Rate limit exceeded: 429 Too Many Requests"),
        RuntimeError("Provider API limit reached"),
    ],
)
async def test_fallback_execution_to_deepseek_on_perplexity_error(error):
    perplexity_provider = MagicMock(spec=PerplexityProvider)
    perplexity_provider.name = "perplexity"
    perplexity_provider.is_active = True
    perplexity_provider.complete = AsyncMock(side_effect=error)

    deepseek_provider = MagicMock(spec=DeepSeekProvider)
    deepseek_provider.name = "deepseek"
    deepseek_provider.is_active = True
    expected_result = CompletionResult(
        text="DeepSeek fallback response",
        provider="deepseek",
        model="deepseek-chat",
    )
    deepseek_provider.complete = AsyncMock(return_value=expected_result)

    manager = ProviderManager([perplexity_provider, deepseek_provider])
    service = AIService(manager)

    result = await service.complete("Hello", purpose="test")

    assert result == expected_result
    perplexity_provider.complete.assert_called_once()
    deepseek_provider.complete.assert_called_once()


@pytest.mark.parametrize(
    "perplexity_key,deepseek_key",
    [
        (None, "ds-key"),
        ("", "ds-key"),
        ("pp-key", None),
        ("pp-key", ""),
        (None, None),
        ("", ""),
    ],
)
def test_provider_initialization_when_api_keys_missing_or_empty(perplexity_key, deepseek_key):
    settings = MagicMock()
    settings.gemini_api_key_1 = "g1-key"
    settings.gemini_api_key_2 = "g2-key"
    settings.gemini_model = "gemini-1.5-flash"
    settings.deepseek_api_key = deepseek_key
    settings.deepseek_model = "deepseek-chat"
    settings.perplexity_api_key = perplexity_key
    settings.perplexity_model = "sonar"

    manager = build_provider_manager(settings)

    deepseek_provider = next(p for p in manager._providers if isinstance(p, DeepSeekProvider))
    perplexity_provider = next(p for p in manager._providers if isinstance(p, PerplexityProvider))

    assert deepseek_provider.api_key == deepseek_key
    assert perplexity_provider.api_key == perplexity_key


def test_individual_provider_instantiation_with_missing_or_empty_key():
    p1 = PerplexityProvider(api_key=None, model="sonar")
    p2 = PerplexityProvider(api_key="", model="sonar")
    d1 = DeepSeekProvider(api_key=None, model="deepseek-chat")
    d2 = DeepSeekProvider(api_key="", model="deepseek-chat")

    assert p1.api_key is None
    assert p2.api_key == ""
    assert d1.api_key is None
    assert d2.api_key == ""