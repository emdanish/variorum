# 2. Provider-agnostic AI layer with automatic fallback

- **Status:** Accepted
- **Date:** 2026-07-26

## Context

The product depends on LLMs for analysis and generation, but no single provider
is reliable enough (quota limits, outages, rate limits) or strategically safe to
depend on exclusively. We have access to multiple keys across multiple vendors
(two Gemini keys, DeepSeek, Perplexity).

## Decision

Application code depends only on the `AIService` facade and the `AIProvider`
interface — never on a concrete vendor SDK. A `ProviderManager` holds an ordered
list of providers and tries them in turn: **Gemini key 1 → Gemini key 2 →
DeepSeek → Perplexity**. Unconfigured providers are skipped; a provider that
errors (quota, auth, transient, bad request) is logged and the next one is tried.
If all fail, a single aggregate error is raised.

Providers are implemented over HTTP with `httpx` rather than vendor SDKs, to keep
the dependency surface small and the providers uniformly testable.

## Consequences

- Callers never choose or switch providers; resilience is automatic.
- Adding or reordering a provider is a change in one wiring function
  (`build_provider_manager`), not across the codebase.
- Fallback ordering and error classification are unit-tested with mock providers,
  so behavior is verified without any network calls.
- Trade-off: HTTP request/response shapes are maintained by us per provider
  instead of relying on SDKs; acceptable given the small, stable surface used.
