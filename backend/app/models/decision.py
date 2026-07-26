from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class DecisionEntry(Base, TimestampMixin):
    """A significant engineering decision, synthesized from ingested history and
    cited back to its sources. The Decision Timeline is the evolving record of
    how a system got the way it is — knowledge in-editor assistants don't keep."""

    __tablename__ = "decision_entries"
    __table_args__ = (Index("ix_decision_entries_repo_decided", "repository_id", "decided_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    # List of {ref, kind, url} citations backing the decision.
    sources: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(128))
