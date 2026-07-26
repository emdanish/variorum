from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingService
from app.models import KnowledgeEntry, KnowledgeKind
from app.services.github.client import HistoryItem


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def upsert_entry(db: Session, repository_id: int, item: HistoryItem) -> None:
    kind = KnowledgeKind(item.kind)
    existing = db.execute(
        select(KnowledgeEntry).where(
            KnowledgeEntry.repository_id == repository_id,
            KnowledgeEntry.kind == kind,
            KnowledgeEntry.source_ref == item.source_ref,
        )
    ).scalar_one_or_none()

    if existing is None:
        db.add(
            KnowledgeEntry(
                repository_id=repository_id,
                kind=kind,
                source_ref=item.source_ref,
                title=item.title,
                body=item.body,
                url=item.url,
                author=item.author,
                occurred_at=_parse_dt(item.occurred_at),
            )
        )
    else:
        existing.title = item.title
        existing.body = item.body
        existing.url = item.url
        existing.author = item.author
        existing.occurred_at = _parse_dt(item.occurred_at)
    db.flush()


def store_items(db: Session, repository_id: int, items: list[HistoryItem]) -> int:
    for item in items:
        if item.source_ref:
            upsert_entry(db, repository_id, item)
    return len([i for i in items if i.source_ref])


def embed_missing(db: Session, repository_id: int, embedder: EmbeddingService) -> int:
    """Compute and store embeddings for entries that don't have one yet. Returns
    the number embedded (0 if embeddings are unavailable)."""
    if not embedder.available:
        return 0
    rows = (
        db.execute(
            select(KnowledgeEntry).where(
                KnowledgeEntry.repository_id == repository_id,
                KnowledgeEntry.embedding.is_(None),
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        return 0
    texts = [f"{e.title or ''}\n\n{e.body or ''}".strip() for e in rows]
    vectors = embedder.embed_batch(texts)
    if not vectors or len(vectors) != len(rows):
        return 0
    for entry, vector in zip(rows, vectors, strict=False):
        entry.embedding = vector
    db.commit()
    return len(rows)
