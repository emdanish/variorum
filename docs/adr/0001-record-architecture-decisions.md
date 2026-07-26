# 1. Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-07-26

## Context

We want the reasoning behind significant technical decisions to survive beyond
the memory of whoever made them — which is, fittingly, the entire premise of the
product.

## Decision

We keep lightweight Architecture Decision Records (ADRs) in `docs/adr/`. Each ADR
is numbered, immutable once accepted, and captures the context, the decision, and
its consequences. Superseding decisions get a new ADR that references the old one.

## Consequences

- Onboarding engineers can read the ADR log to understand *why*, not just *what*.
- The `PROJECT_PLAN.md` stays high-level; detailed rationale lives in ADRs.
