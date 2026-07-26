from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class FileChange(Base, TimestampMixin):
    """One (commit, file) touch, collected from repository history. This is the
    longitudinal churn/authorship dataset behind hotspots and ownership — the
    time-and-people signals that in-editor assistants don't retain."""

    __tablename__ = "file_changes"
    __table_args__ = (
        UniqueConstraint("repository_id", "commit_sha", "path", name="uq_file_change"),
        Index("ix_file_changes_repo_path", "repository_id", "path"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    author: Mapped[str | None] = mapped_column(String(255))
    additions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deletions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_fix: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
