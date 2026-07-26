from __future__ import annotations

import pytest

from app.ai.base import (
    AIProvider,
    AllProvidersFailedError,
    CompletionResult,
    Message,
    ProviderAuthError,
    ProviderQuotaError,
)
from app.ai.manager import ProviderManager
from app.ai.service import build_provider_manager
from app.core.config import Settings


class FakeProvider(AIProvider):
    def __init__(self, name: str, *, configured: bool = True, error: Exception | None = None):
        self.name = name
        self.model = f"{name}-model"
        self._configured = configured
        self._error = error
        self.calls = 0

    @property
    def is_configured(self) -> bool:
        return self._configured

    async def complete(self, messages, *, temperature=0.2, max_tokens=None, json_mode=False):
        self.calls += 1
        if self._error is not None:
            raise self._error
        return CompletionResult(text=f"ok:{self.name}", provider=self.name, model=self.model)


MESSAGES = [Message(role="user", content="hi")]


async def test_first_configured_provider_wins():
    first = FakeProvider("a")
    second = FakeProvider("b")
    manager = ProviderManager([first, second])

    result = await manager.complete(MESSAGES)

    assert result.provider == "a"
    assert first.calls == 1
    assert second.calls == 0


async def test_falls_back_past_quota_error():
    first = FakeProvider("a", error=ProviderQuotaError("a", "quota"))
    second = FakeProvider("b")
    manager = ProviderManager([first, second])

    result = await manager.complete(MESSAGES)

    assert result.provider == "b"
    assert first.calls == 1
    assert second.calls == 1


async def test_skips_unconfigured_without_calling():
    skipped = FakeProvider("a", configured=False)
    used = FakeProvider("b")
    manager = ProviderManager([skipped, used])

    result = await manager.complete(MESSAGES)

    assert result.provider == "b"
    assert skipped.calls == 0


async def test_all_failing_raises_aggregate():
    first = FakeProvider("a", error=ProviderQuotaError("a", "quota"))
    second = FakeProvider("b", error=ProviderAuthError("b", "bad key"))
    manager = ProviderManager([first, second])

    with pytest.raises(AllProvidersFailedError) as exc:
        await manager.complete(MESSAGES)

    assert len(exc.value.errors) == 2


async def test_no_configured_providers_raises_with_no_errors():
    manager = ProviderManager([FakeProvider("a", configured=False)])

    with pytest.raises(AllProvidersFailedError) as exc:
        await manager.complete(MESSAGES)

    assert exc.value.errors == []


def test_default_manager_uses_required_fallback_order():
    settings = Settings(
        _env_file=None,
        gemini_api_key_1="k1",
        gemini_api_key_2="k2",
        deepseek_api_key="k3",
        perplexity_api_key="k4",
    )
    manager = build_provider_manager(settings)

    names = [p.name for p in manager.active_providers]
    assert names == ["perplexity", "deepseek", "gemini-1", "gemini-2"]


def test_default_manager_only_activates_configured_providers():
    settings = Settings(_env_file=None, gemini_api_key_1="k1", perplexity_api_key="k4")
    manager = build_provider_manager(settings)

    assert [p.name for p in manager.active_providers] == ["perplexity", "gemini-1"]
