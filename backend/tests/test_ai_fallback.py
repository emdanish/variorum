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
from app.ai.providers._common import parse_json_object
from app.ai.service import build_provider_manager
from app.core.config import Settings


class FakeProvider(AIProvider):
    def __init__(
        self,
        name: str,
        *,
        configured: bool = True,
        error: Exception | None = None,
        text: str | None = None,
    ):
        self.name = name
        self.model = f"{name}-model"
        self._configured = configured
        self._error = error
        self._text = text
        self.calls = 0

    @property
    def is_configured(self) -> bool:
        return self._configured

    async def complete(self, messages, *, temperature=0.2, max_tokens=None, json_mode=False):
        self.calls += 1
        if self._error is not None:
            raise self._error
        text = self._text if self._text is not None else f"ok:{self.name}"
        return CompletionResult(text=text, provider=self.name, model=self.model)


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
    assert names == ["gemini-1", "gemini-2", "deepseek", "perplexity"]


def test_default_manager_only_activates_configured_providers():
    settings = Settings(_env_file=None, gemini_api_key_1="k1", perplexity_api_key="k4")
    manager = build_provider_manager(settings)

    assert [p.name for p in manager.active_providers] == ["gemini-1", "perplexity"]


# --------------------------------------------------------------------------- #
# JSON-mode: a 200 with unparseable output must fall back to the next provider
# --------------------------------------------------------------------------- #


async def test_json_mode_falls_back_on_unparseable_output():
    bad = FakeProvider("a", text="sorry, I can't do that")  # 200 but not JSON
    good = FakeProvider("b", text='{"ok": true}')
    manager = ProviderManager([bad, good])

    result = await manager.complete(MESSAGES, json_mode=True)

    assert result.provider == "b"
    assert bad.calls == 1 and good.calls == 1


async def test_json_mode_all_unparseable_raises_aggregate():
    manager = ProviderManager([FakeProvider("a", text="nope"), FakeProvider("b", text="also no")])
    with pytest.raises(AllProvidersFailedError) as exc:
        await manager.complete(MESSAGES, json_mode=True)
    assert len(exc.value.errors) == 2


async def test_non_json_mode_accepts_any_text():
    # The same non-JSON text is fine when json_mode is off (prose completion).
    manager = ProviderManager([FakeProvider("a", text="just prose")])
    result = await manager.complete(MESSAGES)
    assert result.text == "just prose"


def test_parse_json_object_recovers_fenced_and_wrapped():
    assert parse_json_object('{"a": 1}') == {"a": 1}
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_object('Here is the result:\n```json\n{"a": 1}\n```\nHope that helps!') == {
        "a": 1
    }
    assert parse_json_object('The answer is {"a": 1} per the data.') == {"a": 1}


def test_parse_json_object_rejects_garbage_and_non_objects():
    for bad in ["not json at all", "[1, 2, 3]", "42", ""]:
        with pytest.raises(ValueError):
            parse_json_object(bad)
