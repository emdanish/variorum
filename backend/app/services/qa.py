from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.ai.service import AIService
from app.models import KnowledgeEntry

MAX_ENTRIES = 8
MAX_BODY_CHARS = 600

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


def retrieve(
    db: Session, repository_id: int, question: str, *, k: int = MAX_ENTRIES
) -> list[KnowledgeEntry]:
    """Full-text retrieval over a repository's knowledge entries, ranked by
    relevance then recency. Falls back to a keyword ILIKE match when full-text
    search yields nothing (e.g. rare identifiers that don't stem)."""
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
