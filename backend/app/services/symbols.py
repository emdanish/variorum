from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingService
from app.core.logging import get_logger
from app.models import CodeSymbol

logger = get_logger("variorum.symbols")

# Only real definitions are worth retrieving/embedding. Imports (often ~half the
# index) are noise for "how does X work" questions and would waste embedding
# quota, so they're excluded from the RAG corpus.
RETRIEVABLE_KINDS = ("function", "method", "class", "interface")

# Bound on symbols embedded per run — a very large repo shouldn't turn one
# re-index into thousands of embedding calls. Anything beyond this is logged,
# never silently dropped, and picked up on the next pass.
MAX_EMBED_PER_RUN = 2000


def symbol_text(symbol: CodeSymbol) -> str:
    """The text embedded for a symbol: what it is, where it lives, its shape."""
    parts = [f"{symbol.kind} {symbol.name}", f"in {symbol.path}"]
    if symbol.signature:
        parts.append(symbol.signature.strip())
    return "\n".join(parts)[:4000]


def embed_missing_symbols(db: Session, repository_id: int, embedder: EmbeddingService) -> int:
    """Compute and store embeddings for code symbols that lack one. Returns the
    number embedded (0 if embeddings are unavailable). Mirror of
    ``knowledge.embed_missing`` — best-effort, capped per run."""
    if not embedder.available:
        return 0
    rows = (
        db.execute(
            select(CodeSymbol)
            .where(
                CodeSymbol.repository_id == repository_id,
                CodeSymbol.embedding.is_(None),
                CodeSymbol.kind.in_(RETRIEVABLE_KINDS),
            )
            .limit(MAX_EMBED_PER_RUN + 1)
        )
        .scalars()
        .all()
    )
    if not rows:
        return 0
    capped = len(rows) > MAX_EMBED_PER_RUN
    batch = rows[:MAX_EMBED_PER_RUN]
    vectors = embedder.embed_batch([symbol_text(s) for s in batch])
    if not vectors or len(vectors) != len(batch):
        return 0
    for symbol, vector in zip(batch, vectors, strict=False):
        symbol.embedding = vector
    db.commit()
    if capped:
        logger.info(
            "symbol embedding capped repo=%s embedded=%d (more remain for next run)",
            repository_id,
            len(batch),
        )
    return len(batch)
