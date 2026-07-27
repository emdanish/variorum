# 6. Code-aware retrieval and index freshness

- **Status:** Accepted
- **Date:** 2026-07-27

## Context

Engineering Memory (cited Q&A) is Variorum's core differentiator, but its
retrieval corpus was history + decisions only — it could answer *why* something
was decided, not *how* the current code works, because the source code itself was
never in the retrieval set. Separately, the code index only refreshed when a user
manually re-indexed, so answers could quietly go stale.

## Decision

**Code-aware retrieval.** Embed `CodeSymbol` rows (name + path + signature) with
the same `gemini-embedding-001` layer and reusable `ai/rag.py` ranking primitive
already used for knowledge and decisions. `qa.retrieve_code` blends semantic
(embedding cosine) with an identifier keyword match; `answer_question` folds code
symbols into the same numbered, cited context alongside history and decisions.
Code citations carry a GitHub blob URL with a line anchor
(`…/blob/<branch>/<path>#L<start>-L<end>`) so a citation jumps the reader to the
exact function. Symbol embedding is best-effort, runs after every index job, and
is capped per run (`MAX_EMBED_PER_RUN`, logged when exceeded — never silently
truncated).

Symbols use JSONB + in-process cosine (no pgvector mirror). At repo scale
(hundreds–low thousands of symbols) the pure-Python rank is trivial; the pgvector
path can be extended to symbols later if a repo's corpus grows large.

**Auto-freshness.** A `push` to a connected repo's *default branch* re-indexes it
via the existing webhook (which now re-embeds symbols too). Feature-branch pushes
are ignored, so only the canonical tree drives a re-index.

## Consequences

- "How does X work?" now answers from the actual code, citing real functions with
  jump-to-line links — the biggest single quality jump to the flagship feature,
  and genuinely actionable (no more grep-hunting).
- One embedding/ranking pattern now serves three corpora; adding a fourth is the
  same shape.
- The index stays current on its own; the manual re-index remains for first setup
  and force-refresh.
- Trade-offs: (1) symbol embeddings cover name/path/signature, not full bodies —
  good for locating code, not a substitute for reading it; storing bodies is a
  future enhancement. (2) Re-index-on-push is coarse (full tree) and inherits the
  documented single-instance / BackgroundTasks limitation; a durable queue with
  incremental indexing is the eventual upgrade. Both are acceptable at current
  scale and keep the $0 posture.
