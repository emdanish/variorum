from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import KnowledgeKind


class KnowledgeEntry(Base, TimestampMixin):
    """A single piece of engineering history — a commit, pull request, issue, or
    review — ingested from GitHub. Phase 2 Q&A retrieves and cites these."""

    __tablename__ = "knowledge_entries"
    __table_args__ = (
        UniqueConstraint(
            "repository_id", "kind", "source_ref", name="uq_knowledge_repo_kind_ref"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[KnowledgeKind] = mapped_column(nullable=False)
    source_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str | None] = mapped_column(String(1024))
    body: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(1024))
    author: Mapped[str | None] = mapped_column(String(255))
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Semantic-search embedding stored as a JSON array of floats. (pgvector is
    # the production upgrade; JSONB + in-process cosine avoids that dependency.)
    embedding: Mapped[list[float] | None] = mapped_column(JSONB)
