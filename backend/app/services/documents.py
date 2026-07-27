from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingService
from app.models import Document


def document_text(doc: Document) -> str:
    """Text embedded for a document: its title plus body."""
    return f"{doc.title or ''}\n\n{doc.body or ''}".strip()


def embed_missing_documents(db: Session, repository_id: int, embedder: EmbeddingService) -> int:
    """Compute and store embeddings for documents (with body) that lack one.
    Returns the number embedded (0 if unavailable). Best-effort."""
    if not embedder.available:
        return 0
    rows = (
        db.execute(
            select(Document).where(
                Document.repository_id == repository_id,
                Document.embedding.is_(None),
                Document.body.is_not(None),
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        return 0
    vectors = embedder.embed_batch([document_text(d) for d in rows])
    if not vectors or len(vectors) != len(rows):
        return 0
    for doc, vector in zip(rows, vectors, strict=False):
        doc.embedding = vector
    db.commit()
    return len(rows)
