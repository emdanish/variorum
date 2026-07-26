from __future__ import annotations

import math
import re
from dataclasses import dataclass

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingService
from app.ai.service import AIService
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import KnowledgeEntry

logger = get_logger("variorum.qa")

MAX_ENTRIES = 8
MAX_BODY_CHARS = 600
MIN_SIMILARITY = 0.4  # cosine floor to exclude clearly-unrelated vector hits

# Detected once per process: is the pgvector acceleration path available? True
# only when the `vector` extension is installed AND the `embedding_vec` column
# exists (both created by the guarded pgvector migration). Everywhere else —
# including this dev DB and the test suite — retrieval uses the in-process
# cosine path over the JSONB `embedding` column, which is always present.
_pgvector_active: bool | None = None


def reset_pgvector_detection() -> None:
    """Clear the cached detection (used by tests)."""
    global _pgvector_active
    _pgvector_active = None


def pgvector_active(db: Session) -> bool:
    global _pgvector_active
    if not get_settings().pgvector_enabled:
        return False
    if _pgvector_active is None:
        try:
            _pgvector_active = bool(
                db.execute(
                    text(
                        "SELECT (EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') "
                        "AND EXISTS (SELECT 1 FROM information_schema.columns "
                        "WHERE table_name = 'knowledge_entries' "
                        "AND column_name = 'embedding_vec'))"
                    )
                ).scalar()
            )
        except Exception:  # noqa: BLE001 — detection must never break retrieval
            _pgvector_active = False
    return _pgvector_active

SYSTEM_PROMPT = (
    "You are Variorum's engineering-memory assistant. Answer the question using "
    "ONLY the numbered context entries below (commits, pull requests, issues). "
    "Rules:\n"
    "- Base every statement on the provided context; never invent facts, APIs, or "
    "history.\n"
    "- Cite the entries you used by their number.\n"
    "- If the context does not contain the answer, say you don't have enough "
    "information and cite nothing.\n"
    'Respond in strict JSON: {"answer": string, "cited": [int, ...]}'
)


@dataclass
class QAResult:
    answer: str
    cited_entries: list[KnowledgeEntry]
    provider: str | None
    model: str | None


def _haystack():
    return func.coalesce(KnowledgeEntry.title, "") + " " + func.coalesce(KnowledgeEntry.body, "")


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _merge(
    primary: list[KnowledgeEntry], secondary: list[KnowledgeEntry], k: int
) -> list[KnowledgeEntry]:
    seen: set[int] = set()
    out: list[KnowledgeEntry] = []
    for entry in [*primary, *secondary]:
        if entry.id in seen:
            continue
        seen.add(entry.id)
        out.append(entry)
        if len(out) >= k:
            break
    return out


def retrieve(
    db: Session,
    repository_id: int,
    question: str,
    *,
    k: int = MAX_ENTRIES,
    embedder: EmbeddingService | None = None,
) -> list[KnowledgeEntry]:
    """Hybrid retrieval: semantic (embedding cosine) blended with keyword
    full-text search. Falls back to keyword-only when embeddings are
    unavailable (no embedder, no quota, or nothing embedded)."""
    keyword_hits = _keyword_retrieve(db, repository_id, question, k)
    if embedder is None or not embedder.available:
        return keyword_hits

    query_vec = embedder.embed(question)
    if not query_vec:
        return keyword_hits

    if pgvector_active(db):
        vector_hits = _vector_retrieve_pg(db, repository_id, query_vec, k)
    else:
        vector_hits = _vector_retrieve_inprocess(db, repository_id, query_vec, k)

    return _merge(vector_hits, keyword_hits, k)


def _vector_retrieve_inprocess(
    db: Session, repository_id: int, query_vec: list[float], k: int
) -> list[KnowledgeEntry]:
    """Rank JSONB-stored embeddings with pure-Python cosine. Fine at MVP scale;
    the pgvector path replaces this loop with an indexed SQL query."""
    embedded = (
        db.execute(
            select(KnowledgeEntry).where(
                KnowledgeEntry.repository_id == repository_id,
                KnowledgeEntry.embedding.is_not(None),
            )
        )
        .scalars()
        .all()
    )
    scored = [(_cosine(query_vec, e.embedding or []), e) for e in embedded]
    ranked = sorted(scored, key=lambda s: s[0], reverse=True)
    return [e for score, e in ranked if score >= MIN_SIMILARITY][:k]


def _vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


def _vector_retrieve_pg(
    db: Session, repository_id: int, query_vec: list[float], k: int
) -> list[KnowledgeEntry]:
    """Indexed nearest-neighbour search via pgvector's cosine-distance operator.
    Scales to large repositories — the database does the ranking, not Python."""
    max_distance = 1.0 - MIN_SIMILARITY
    rows = db.execute(
        text(
            "SELECT id, embedding_vec <=> (:qvec)::vector AS dist "
            "FROM knowledge_entries "
            "WHERE repository_id = :rid AND embedding_vec IS NOT NULL "
            "ORDER BY dist ASC LIMIT :k"
        ),
        {"qvec": _vector_literal(query_vec), "rid": repository_id, "k": k},
    ).all()
    ids = [row.id for row in rows if row.dist <= max_distance]
    if not ids:
        return []
    entries = (
        db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id.in_(ids))).scalars().all()
    )
    by_id = {e.id: e for e in entries}
    return [by_id[i] for i in ids if i in by_id]


def _keyword_retrieve(
    db: Session, repository_id: int, question: str, k: int
) -> list[KnowledgeEntry]:
    """Full-text retrieval ranked by relevance then recency, with a keyword
    ILIKE fallback for rare identifiers that don't stem."""
    tsv = func.to_tsvector("english", _haystack())
    tsq = func.websearch_to_tsquery("english", question)
    rows = (
        db.execute(
            select(KnowledgeEntry)
            .where(KnowledgeEntry.repository_id == repository_id, tsv.op("@@")(tsq))
            .order_by(func.ts_rank(tsv, tsq).desc(), KnowledgeEntry.occurred_at.desc())
            .limit(k)
        )
        .scalars()
        .all()
    )
    if rows:
        return list(rows)

    words = re.findall(r"[A-Za-z0-9_]{3,}", question)[:6]
    if not words:
        return []
    haystack = _haystack()
    clauses = [haystack.ilike(f"%{w}%") for w in words]
    return list(
        db.execute(
            select(KnowledgeEntry)
            .where(KnowledgeEntry.repository_id == repository_id, or_(*clauses))
            .order_by(KnowledgeEntry.occurred_at.desc())
            .limit(k)
        )
        .scalars()
        .all()
    )


def _format_context(entries: list[KnowledgeEntry]) -> str:
    blocks = []
    for i, e in enumerate(entries, start=1):
        body = (e.body or "").strip()
        if len(body) > MAX_BODY_CHARS:
            body = body[:MAX_BODY_CHARS] + " …"
        ref = f"{e.kind.value} {e.source_ref}"
        blocks.append(f"[{i}] {ref} — {e.title or ''}\n{body}\n(source: {e.url or 'n/a'})")
    return "\n\n".join(blocks)


async def answer_question(
    ai: AIService, question: str, entries: list[KnowledgeEntry]
) -> QAResult:
    if not entries:
        return QAResult(
            answer=(
                "I don't have enough indexed history to answer that yet. "
                "Try ingesting this repository's history first."
            ),
            cited_entries=[],
            provider=None,
            model=None,
        )

    prompt = f"Question: {question}\n\nContext:\n{_format_context(entries)}"
    data, result = await ai.complete_structured(
        prompt, system=SYSTEM_PROMPT, purpose="engineering_qa"
    )
    answer = str(data.get("answer", "")).strip()
    cited_idx = {
        n for n in (data.get("cited") or []) if isinstance(n, int) and 1 <= n <= len(entries)
    }
    cited = [entries[n - 1] for n in sorted(cited_idx)]
    return QAResult(
        answer=answer or "I don't have enough information to answer that.",
        cited_entries=cited,
        provider=result.provider,
        model=result.model,
    )
