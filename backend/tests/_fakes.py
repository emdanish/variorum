from __future__ import annotations

from app.ai.base import CompletionResult


class FakeAI:
    """Duck-typed stand-in for AIService used in analysis tests."""

    def __init__(
        self,
        verdict: dict | None = None,
        *,
        text: str = "updated content",
        available: bool = True,
        provider: str = "gemini-1",
        model: str = "gemini-test",
    ) -> None:
        self._verdict = verdict or {}
        self._text = text
        self._available = available
        self.provider = provider
        self.model = model
        self.calls: list[str] = []

    @property
    def available(self) -> bool:
        return self._available

    async def complete(self, prompt: str, *, system: str | None = None, **_kwargs):
        self.calls.append(prompt)
        return CompletionResult(text=self._text, provider=self.provider, model=self.model)

    async def complete_structured(self, prompt: str, *, system: str | None = None, **_kwargs):
        self.calls.append(prompt)
        return dict(self._verdict), CompletionResult(
            text="", provider=self.provider, model=self.model
        )
