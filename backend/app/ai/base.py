from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class Message:
    role: Role
    content: str


@dataclass
class CompletionResult:
    text: str
    provider: str
    model: str
    latency_ms: int | None = None
    raw: dict | None = field(default=None, repr=False)


class ErrorKind(str, Enum):
    not_configured = "not_configured"
    auth = "auth"
    quota = "quota"
    transient = "transient"
    bad_request = "bad_request"
    unknown = "unknown"


class ProviderError(Exception):
    """Base class for provider failures. Every subclass is fallback-eligible:
    the manager logs it and advances to the next provider."""

    kind: ErrorKind = ErrorKind.unknown

    def __init__(self, provider: str, message: str, *, status_code: int | None = None) -> None:
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}")


class ProviderNotConfiguredError(ProviderError):
    kind = ErrorKind.not_configured


class ProviderAuthError(ProviderError):
    kind = ErrorKind.auth


class ProviderQuotaError(ProviderError):
    kind = ErrorKind.quota


class ProviderTransientError(ProviderError):
    kind = ErrorKind.transient


class ProviderBadRequestError(ProviderError):
    kind = ErrorKind.bad_request


class AllProvidersFailedError(Exception):
    """Raised when every configured provider failed. Carries the per-provider
    errors so callers and observability can see exactly what happened."""

    def __init__(self, errors: list[ProviderError]) -> None:
        self.errors = errors
        detail = "; ".join(str(err) for err in errors) or "no providers configured"
        super().__init__(f"All AI providers failed: {detail}")


class AIProvider(abc.ABC):
    """Uniform interface every provider implements. Application code depends on
    this, never on a concrete vendor."""

    name: str
    model: str

    @property
    @abc.abstractmethod
    def is_configured(self) -> bool:
        """True when this provider has the credentials it needs to be tried."""

    @abc.abstractmethod
    async def complete(
        self,
        messages: list[Message],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> CompletionResult:
        """Return a completion or raise a ProviderError subclass."""
