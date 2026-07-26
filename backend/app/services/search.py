from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import CodeSymbol, DecisionEntry, Document, KnowledgeEntry


def unified_search(db: Session, repository_id: int, query: str, *, limit: int = 8) -> dict:
    """Search a repository across code symbols, documentation, decisions, and
    ingested history in one call. Substring match — fast, no AI."""
    like = f"%{query}%"

    symbols = (
        db.execute(
            select(CodeSymbol)
            .where(
                CodeSymbol.repository_id == repository_id,
                or_(CodeSymbol.name.ilike(like), CodeSymbol.path.ilike(like)),
            )
            .limit(limit)
        )
        .scalars()
        .all()
    )
    documents = (
        db.execute(
            select(Document)
            .where(
                Document.repository_id == repository_id,
                or_(Document.path.ilike(like), Document.title.ilike(like)),
            )
            .limit(limit)
        )
        .scalars()
        .all()
    )
    decisions = (
        db.execute(
            select(DecisionEntry)
            .where(
                DecisionEntry.repository_id == repository_id,
                or_(DecisionEntry.title.ilike(like), DecisionEntry.summary.ilike(like)),
            )
            .order_by(DecisionEntry.decided_at.desc().nullslast())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    knowledge = (
        db.execute(
            select(KnowledgeEntry)
            .where(
                KnowledgeEntry.repository_id == repository_id,
                or_(KnowledgeEntry.title.ilike(like), KnowledgeEntry.body.ilike(like)),
            )
            .order_by(KnowledgeEntry.occurred_at.desc().nullslast())
            .limit(limit)
        )
        .scalars()
        .all()
    )

    return {
        "query": query,
        "symbols": [
            {"name": s.name, "path": s.path, "kind": s.kind, "language": s.language}
            for s in symbols
        ],
        "documents": [{"path": d.path, "title": d.title} for d in documents],
        "decisions": [
            {"id": d.id, "title": d.title, "summary": d.summary, "decided_at": d.decided_at}
            for d in decisions
        ],
        "knowledge": [
            {"kind": k.kind.value, "source_ref": k.source_ref, "title": k.title, "url": k.url}
            for k in knowledge
        ],
        "total": len(symbols) + len(documents) + len(decisions) + len(knowledge),
    }
