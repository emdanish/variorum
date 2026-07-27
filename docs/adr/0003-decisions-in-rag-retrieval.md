# 3. Synthesized decisions in the RAG retrieval corpus

- **Status:** Accepted
- **Date:** 2026-07-27

## Context

Embeddings and RAG already existed over ingested history (`KnowledgeEntry` —
commits, PRs, issues), with a hybrid semantic⊕keyword retriever and cited
answers. But the engineering-memory Q&A ("why is the system this way?") drew only
on raw history. The **Decision Timeline** (`DecisionEntry`) — AI-synthesized
"why" records with a `title` and `summary` — is the highest-signal source for
exactly that question, yet it was embedded nowhere and invisible to retrieval.

## Decision

Extend the existing foundation rather than rebuild it:

- A reusable ranking core (`app/ai/rag.py`: `cosine`, `top_k_by_cosine`) is the
  shared in-process semantic primitive; `services/qa.py` ranks through it.
- `DecisionEntry` gets a JSONB `embedding` column, populated when a timeline is
  synthesized, with an `embed_missing_decisions` backfill. Decisions are few per
  repo, so JSONB + in-process cosine is used — no pgvector mirror.
- `retrieve_decisions()` (semantic + keyword with an ILIKE fallback) runs
  alongside history retrieval, and `answer_question` blends decisions into one
  numbered, cited context **additively** (decisions default to empty, so the
  history-only path is unchanged). Decision citations carry `kind="decision"`.

`Document` (no stored body text) and code symbols (high volume, low "why" signal)
are deliberately left on keyword search via unified search.

## Consequences

- "Ask" reasons over distilled decisions, not just commit/PR noise; citations
  point at the recorded rationale.
- The retrieval mechanics are a shared primitive, so future embedded content
  types plug in without duplicating cosine/top-k logic.
- The working history-only Q&A path is untouched (additive signature, defaulted
  argument) — verified by the pre-existing qa tests still passing.
- Trade-off: two embedded corpora with slightly different storage (knowledge has
  the optional pgvector mirror; decisions are JSONB-only). Justified by their
  very different cardinality.
