# 7. The Change Briefing — synthesis over new intelligence

- **Status:** Accepted
- **Date:** 2026-07-27

## Context

The Phase 5 strategy exercise identified the single "cannot work without it"
workflow: before touching code, a developer wants one answer to *"I'm about to
change X — what do I need to know?"* — where it lives, how risky it is, who to
ask, why it's built that way, what will drift, and what to test. Every piece of
that already existed in Variorum as a separate surface (code index, hotspots,
ownership, decisions, history, doc↔code links, risk findings). What was missing
was the *synthesis* at the moment of intent.

## Decision

Add a **Change Briefing** that orchestrates existing services into one cited,
pre-work answer — it introduces no new data source. `build_change_briefing`
takes a plain-English intent, uses code-aware retrieval (Tier 1) to locate the
relevant symbols/files, then joins in per-file hotspot risk + test presence,
module ownership (surfacing single-owner/bus-factor-1 areas as "who to loop in"),
relevant decisions + history ("why it's this way"), documents linked to those
files ("docs that will drift"), and untested touched files ("tests to add").

The core is **deterministic and reliable** — it works with zero AI, degrading to
keyword retrieval when embeddings are unavailable. A short AI "before you start"
TL;DR is layered on top **best-effort**: if the provider is unavailable or errors,
the structured briefing stands on its own. This keeps the flagship trustworthy
under the free-tier quota reality (429s) that a purely-AI feature would fail on.

Exposed as `POST /repositories/{id}/change-briefing` and a prominent "Plan a
change" panel at the top of the repository page.

## Consequences

- The highest-value workflow is delivered by wiring, not new infrastructure —
  low risk, and it makes every prior phase's data pull its weight.
- Actionable by construction: every section is a next step (open this file, ask
  this person, update this doc, add this test), not a stat.
- Reliability-first: the deterministic core means the feature never hard-fails on
  AI quota; the TL;DR is a bonus.
- Trade-off: retrieval quality for the "where" depends on the code embeddings /
  keyword match, so a vaguely-worded intent yields a looser briefing. Acceptable —
  the developer refines the phrasing, same as any search.
- The Change Briefing (pre-work, no PR yet) and the PR Impact Briefing (post-hoc,
  on an existing PR) are deliberately separate surfaces for the two moments.
