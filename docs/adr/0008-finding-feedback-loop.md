# 8. Finding feedback loop — dismiss means "stop nagging me"

- **Status:** Accepted
- **Date:** 2026-07-27

## Context

On free-tier models, signal-to-noise *is* the product. Drift and risk findings
are re-created every time a PR is re-analyzed (webhook + manual, or a new commit),
and the supersede logic only de-duplicated *un-actioned* findings within the same
run. A finding a user had deliberately **dismissed** would come straight back on
the next analysis — training the user to ignore the tool. Dismissing taught the
system nothing.

## Decision

Add a lightweight **suppression** that closes the loop:

- A `Suppression` row keyed by `(repository_id, kind, target)` — `kind` is
  `drift` or `risk`; `target` is the document path (drift) or file path (risk).
- **Dismissing** a finding records a suppression for its target; **restoring**
  lifts it. The user's decision is now durable state, not a per-run status.
- When the analysis workers create findings, they skip any target with an active
  suppression (count logged, never silently dropped) — so re-analysis doesn't
  resurface what the user already waved off.

Suppression is by target, giving the predictable contract users expect from a
dismiss button: *"don't flag this file/doc again until I restore it."*

## Consequences

- Dismiss is now meaningful: the noise a reviewer clears stays cleared, so the
  findings that remain are the ones they haven't judged — trust compounds.
- Fully deterministic and AI-independent; verifiable without any provider quota.
- Restore is the escape hatch — re-enables flagging for that target.
- Trade-off: a target-level suppression also hides *genuinely new* drift/risk for
  that same file until restored. Accepted for v1 as the least-surprising
  behavior. A future refinement can scope suppression to a content signature (the
  doc's `content_hash` / the finding's evidence) so it auto-expires when the
  underlying situation materially changes — near-duplicate suppression without
  hiding new problems.
