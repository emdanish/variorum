from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingService
from app.ai.service import AIService
from app.models import DecisionEntry, KnowledgeEntry, KnowledgeKind

# Prefer PRs and issues (they carry rationale) over bare commits, and keep the
# context compact.
_MAX_CONTEXT = 40
_MAX_BODY = 320
_MAX_DECISIONS = 12
_KIND_PRIORITY = {
    KnowledgeKind.pull_request: 0,
    KnowledgeKind.issue: 1,
    KnowledgeKind.review: 2,
    KnowledgeKind.commit: 3,
}

SYSTEM_PROMPT = (
    "You are Variorum's engineering historian. From the numbered history entries "
    "below (pull requests, issues, commits), extract the SIGNIFICANT engineering "
    "decisions — architectural choices, tradeoffs, notable workarounds, or "
    "direction changes. Ignore routine changes.\n"
    "Rules:\n"
    "- Base every decision only on the provided entries; never invent history.\n"
    "- Each decision must cite the entry numbers it is drawn from.\n"
    "- 'summary' states what was decided AND why, in 1-3 sentences.\n"
    f"- Return at most {_MAX_DECISIONS}, most significant first.\n"
    'Respond in strict JSON: {"decisions": [{"title": string, "summary": string, '
    '"cited": [int, ...]}]}'
)


def gather_entries(db: Session, repository_id: int) -> list[KnowledgeEntry]:
    entries = list(
        db.execute(
            select(KnowledgeEntry).where(KnowledgeEntry.repository_id == repository_id)
        )
        .scalars()
        .all()
    )
    entries.sort(
        key=lambda e: (
            _KIND_PRIORITY.get(e.kind, 9),
            -(e.occurred_at.timestamp() if e.occurred_at else 0.0),
        )
    )
    return entries[:_MAX_CONTEXT]


def build_prompt(entries: list[KnowledgeEntry]) -> str:
    lines = []
    for i, e in enumerate(entries, start=1):
        date = e.occurred_at.date().isoformat() if e.occurred_at else "n/a"
        body = (e.body or "").strip().replace("\n", " ")[:_MAX_BODY]
        lines.append(f"[{i}] {e.kind.value} {e.source_ref} ({date}) — {e.title or ''}\n{body}")
    return "History entries:\n" + "\n\n".join(lines)


def _parse(data: dict, entries: list[KnowledgeEntry]) -> list[dict]:
    raw = data.get("decisions")
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw[:_MAX_DECISIONS]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        summary = str(item.get("summary", "")).strip()
        if not title or not summary:
            continue
        cited_idx = {
            n for n in (item.get("cited") or []) if isinstance(n, int) and 1 <= n <= len(entries)
        }
        cited = [entries[n - 1] for n in sorted(cited_idx)]
        sources = [
            {"ref": e.source_ref, "kind": e.kind.value, "url": e.url} for e in cited
        ]
        dates = [e.occurred_at for e in cited if e.occurred_at]
        decided_at = min(dates) if dates else None
        out.append(
            {"title": title[:300], "summary": summary[:2000], "sources": sources,
             "decided_at": decided_at}
        )
    return out


async def generate_decisions(
    ai: AIService, entries: list[KnowledgeEntry]
) -> tuple[list[dict], str | None, str | None]:
    data, result = await ai.complete_structured(
        build_prompt(entries), system=SYSTEM_PROMPT, purpose="decision_timeline"
    )
    return _parse(data, entries), result.provider, result.model


def _embedding_text(title: str, summary: str) -> str:
    return f"{title}\n\n{summary}".strip()


def replace_decisions(
    db: Session,
    repository_id: int,
    decisions: list[dict],
    *,
    provider: str | None,
    model: str | None,
    embedder: EmbeddingService | None = None,
) -> int:
    """Replace the repository's decision timeline with a freshly synthesized set.

    When an embedder is supplied and available, embeddings are computed for the
    new rows so decisions are immediately retrievable in the Q&A. Embedding is
    best-effort — a failure leaves ``embedding`` NULL and never blocks the write
    (``embed_missing_decisions`` can backfill later)."""
    db.query(DecisionEntry).filter(DecisionEntry.repository_id == repository_id).delete()
    rows = [
        DecisionEntry(
            repository_id=repository_id,
            title=d["title"],
            summary=d["summary"],
            sources=d["sources"],
            decided_at=d["decided_at"],
            provider=provider,
            model=model,
        )
        for d in decisions
    ]
    db.add_all(rows)
    if rows and embedder is not None and embedder.available:
        vectors = embedder.embed_batch([_embedding_text(r.title, r.summary) for r in rows])
        if vectors and len(vectors) == len(rows):
            for row, vector in zip(rows, vectors, strict=False):
                row.embedding = vector
    db.commit()
    return len(rows)


def embed_missing_decisions(
    db: Session, repository_id: int, embedder: EmbeddingService
) -> int:
    """Compute and store embeddings for decisions that lack one. Returns the
    number embedded (0 if embeddings are unavailable). Mirror of
    ``knowledge.embed_missing`` — a safety net for rows written without an
    embedder (older data, or a transient embedding outage)."""
    if not embedder.available:
        return 0
    rows = (
        db.execute(
            select(DecisionEntry).where(
                DecisionEntry.repository_id == repository_id,
                DecisionEntry.embedding.is_(None),
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        return 0
    vectors = embedder.embed_batch([_embedding_text(r.title, r.summary) for r in rows])
    if not vectors or len(vectors) != len(rows):
        return 0
    for row, vector in zip(rows, vectors, strict=False):
        row.embedding = vector
    db.commit()
    return len(rows)


def list_decisions(db: Session, repository_id: int) -> list[DecisionEntry]:
    return list(
        db.execute(
            select(DecisionEntry)
            .where(DecisionEntry.repository_id == repository_id)
            .order_by(DecisionEntry.decided_at.desc().nullslast(), DecisionEntry.id.desc())
        )
        .scalars()
        .all()
    )
